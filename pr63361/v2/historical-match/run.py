"""Two Python token lists + old hashes -> full native-compatible new hashes.

All native Request construction, matching, conversion, seeded hash copying and
native suffix hashing are timed. Input/oracle construction and equality checks
are outside timers. No model, scheduler or GPU operation is run.
"""
import gc
import hashlib
import json
import os
import platform
import random
import statistics as stat
import subprocess
import sys
import time
from array import array
from pathlib import Path

import matcher
import vllm
from vllm.sampling_params import SamplingParams
from vllm.utils.hashing import sha256
from vllm.v1.core import kv_cache_utils
from vllm.v1.request import Request

BS = 16
REPS, SAMPLES, WARMUP, PAIRS = 3, 120, 12, 8
SEED = 42
kv_cache_utils.init_none_hash(sha256)
NATIVE = kv_cache_utils.get_request_block_hasher(BS, sha256)
PARAMS = SamplingParams(max_tokens=1)


def native_hash(tokens):
    return Request('oracle', tokens, PARAMS, None, block_hasher=NATIVE).block_hashes


def python_lcp(a, b, n):
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n


def gallop(a, b, n):
    lo, step = 0, 1
    while lo < n:
        hi = min(n, lo+step)
        if a[lo:hi] != b[lo:hi]:
            while hi-lo > 1:
                mid = (lo+hi)//2
                if a[lo:mid] == b[lo:mid]:
                    lo = mid
                else:
                    hi = mid
            return lo
        lo, step = hi, step*2
    return n


def array_gallop(a, b, n):
    return gallop(array('I', a), array('I', b), n)


def packed(a, b, n, avx):
    # Both lists are converted on every call: primary input contract is lists.
    return matcher.buffer_lcp(array('I', a), array('I', b), n, avx)


METHODS = {
    'native': lambda a,b,n: 0,
    'max_or_native': lambda a,b,n: n if a[:n] == b[:n] else 0,
    'python_loop': python_lcp,
    'gallop_list': gallop,
    'gallop_array': array_gallop,
    'c_list_equal': lambda a,b,n: matcher.list_lcp(a,b,n,False),
    'c_list_unbox': lambda a,b,n: matcher.list_lcp(a,b,n,True),
    'packed_word': lambda a,b,n: packed(a,b,n,False),
    'packed_avx2': lambda a,b,n: packed(a,b,n,True),
}


def produce(method, old, new, old_hashes):
    n = min(len(old_hashes), len(new)//BS)*BS
    matched = METHODS[method](old, new, n)//BS

    def seeded(request):
        request.block_hashes.extend(old_hashes[:matched])
        return NATIVE(request)

    # Same wrapper/Request lifecycle for every arm, including native baseline.
    r = Request('bench', new, PARAMS, None, block_hasher=seeded)
    return r.block_hashes


def clone(a):
    return json.loads(json.dumps(a))


def verify():
    checks = 0
    rng = random.Random(SEED)
    for length in (0,1,15,16,17,31,32,33,63,64,65,255):
        old = [rng.randrange(1000,200000) for _ in range(length)]
        # Exercise full uint32 values and partial blocks too.
        if old:
            old[-1] = 2**32-1
        news = [old, old[:max(0,length-7)], old+[1001]*19]
        for p in sorted(set((0,length//2,max(0,length-1)))):
            if length:
                edited = old.copy(); edited[p] ^= 1; news.append(edited)
        for new in news:
            a,b = clone(old),clone(new)
            hs,expected = native_hash(a),native_hash(b)
            limit=min(len(hs),len(b)//BS)*BS
            lcp=python_lcp(a,b,limit)
            for method,fn in METHODS.items():
                if method not in ('native','max_or_native'):
                    assert fn(a,b,limit)==lcp,(length,method,lcp)
                assert produce(method,a,b,hs)==expected,(length,method)
                checks+=1
    # Boundary positions across every SIMD lane, word, and block boundary.
    for length in (7,8,9,15,16,17,31,32,33,129):
        for pos in range(length):
            a=[1000+i for i in range(length)]; b=clone(a);b[pos]^=1
            for avx in (False,True):
                assert packed(a,b,length,avx)==pos,(length,pos,avx)
                checks+=1
    Path('correctness.json').write_text(json.dumps({'passed':True,'checks':checks},indent=2))


def make_pairs(length, case):
    pairs=[]
    rng=random.Random(SEED+length)
    for _ in range(PAIRS):
        old=[rng.randrange(1000,200000) for _ in range(length)]
        new=old.copy()
        if case=='append':
            new.extend(rng.randrange(1000,200000) for _ in range(256))
        elif case=='head':
            new[0]^=1
        elif case=='middle':
            new[length//2+3]^=1
        elif case=='tail':
            new[-3]^=1
        elif case=='shorten':
            new=new[:-256]
        a,b=clone(old),clone(new)
        assert all(x is not y for x,y in zip(a,b)), 'unfair shared int objects'
        hs,expected=native_hash(a),native_hash(b)
        matched=python_lcp(a,b,min(len(hs),len(b)//BS)*BS)//BS
        pairs.append((a,b,hs,expected,matched))
    return pairs


def main():
    assert array('I').itemsize==4
    allowed=sorted(os.sched_getaffinity(0))
    # Pin to one allowed core; record host activity, not claiming exclusivity.
    core=allowed[len(allowed)//2]
    os.sched_setaffinity(0,{core})
    src={}
    for p in (Path(kv_cache_utils.__file__),Path(sys.modules[Request.__module__].__file__)):
        src[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    expected=json.loads(Path('expected-native.json').read_text())
    assert src==expected, ('native source changed',src,expected)
    env={'python':sys.version,'vllm':vllm.__version__,'platform':platform.platform(),
         'affinity_before':allowed,'pinned_core':core,'native_features':matcher.features(),
         'source_sha256':src,'compiler':subprocess.check_output(['gcc','--version'],text=True),
         'gc_enabled':gc.isenabled(),
         'config':{'block_size':BS,'hash':'sha256','repetitions':REPS,'samples':SAMPLES,
                   'warmup':WARMUP,'pairs':PAIRS,'seed':SEED},
         'source_files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in Path('.').iterdir() if p.suffix in ('.py','.c','.sh','.md')}}
    Path('environment.json').write_text(json.dumps(env,indent=2))
    verify()
    rows=[]
    order_rng=random.Random(SEED)
    with Path('samples.jsonl').open('w') as output:
        for length in (4096,16384,65536):
            for case in ('same','append','head','middle','tail','shorten'):
                pairs=make_pairs(length,case)
                for rep in range(REPS):
                    order=list(METHODS);order_rng.shuffle(order)
                    for method in order:
                        for i in range(WARMUP):
                            a,b,hs,expected,_=pairs[i%PAIRS]
                            assert produce(method,a,b,hs)==expected
                        samples=[]
                        for i in range(SAMPLES):
                            a,b,hs,expected,_=pairs[i%PAIRS]
                            start=time.perf_counter_ns()
                            result=produce(method,a,b,hs)
                            elapsed=time.perf_counter_ns()-start
                            assert result==expected,(length,case,rep,method,i)
                            del result
                            samples.append(elapsed)
                        ordered=sorted(samples)
                        row={'length':length,'case':case,'rep':rep,'method':method,
                             'order':order,'samples_ns':samples,'median_us':stat.median(samples)/1000,
                             'p95_us':ordered[(95*len(ordered)+99)//100-1]/1000,
                             'output_blocks':len(pairs[0][3]),'max_reusable_blocks':pairs[0][4],
                             'verified_samples':len(samples)}
                        rows.append(row)
                        output.write(json.dumps(row)+'\n');output.flush()
                        print(json.dumps({k:v for k,v in row.items() if k not in ('samples_ns','order')}),flush=True)
    Path('results.json').write_text(json.dumps({'passed':True,'rows':rows},indent=2))
    subprocess.run(['bash','-c','lscpu > lscpu.txt; cat /proc/loadavg > load-after.txt'],check=True)


if __name__=='__main__':
    main()
