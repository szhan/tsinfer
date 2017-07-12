

import subprocess
import os
import numpy as np
import itertools
import multiprocessing
import pandas as pd
import random
import statistics
import sys
import attr
import collections
import concurrent.futures
import time
import random
import threading
import math
import resource
import operator
import heapq
import sortedcontainers
# import profilehooks

import humanize
import h5py
import tqdm
import psutil
import svgwrite
import colour

script_path = __file__ if "__file__" in locals() else "./dummy.py"
sys.path.insert(1,os.path.join(os.path.dirname(os.path.abspath(script_path)),'..','msprime')) # use the local copy of msprime in preference to the global one
sys.path.insert(1,os.path.join(os.path.dirname(os.path.abspath(script_path)),'..','tsinfer')) # use the local copy of tsinfer in preference to the global one


import tsinfer
import _tsinfer
import msprime
import msprime_to_inference_matrices


def draw_segments(segments, L):
    print("   ", "-" * L)
    for seg in segments:
        s = "{:<4d}".format(seg.value)
        s += " " * (seg.start - 0)
        s += "=" * (seg.end - seg.start)
        print(s)
    print("   ", "-" * L)


def overlap_algorithm_dev(num_chunk_segments, chunk_bounds, seed=1, duplicate_proba=0.5):
    random.seed(seed)
    # Generate some random segments.
    segments = []
    j = 0
    for start, end in chunk_bounds:
        for _ in range(num_chunk_segments):
            x = random.randint(start, end)
            y = random.randint(start, end)
            while x == y:
                y = random.randint(start, end)
            segments.append(tsinfer.Segment(*sorted([x, y]), value=j))
            while random.random() < duplicate_proba:
                # With probability duplicate_proba create a copy.
                segments.append(tsinfer.Segment(*sorted([x, y]), value=j))

            j += 1
        # print(segments)
    L = max(end for start, end in chunk_bounds)

    # while True:
    #     segments = trim_segments(segments, L)
    #     print("==================LOOP=========================")

    # draw_segments(segments, L)
    # filtered_equal = find_identical_overlaps(segments, L)
    # draw_segments(filtered_equal, L)
    # o1 = pairwise_find_max_overlap(segments, L)
    # o2 = find_max_overlap(segments, L)
    # assert o1 == o2
    o1 = find_nonoverlapping(segments, L)
    o2 = pairwise_find_nonoverlapping(segments, L)
    # print(o1)
    # print(o2)
    assert o1 == o2


def pairwise_find_nonoverlapping(S, L):
    S.sort(key=lambda x: (x.start, -x.end))
    n = len(S)
    ret = []
    for j in range(n):
        overlaps = 0
        for k in range(n):
            if j != k:
                overlap = min(S[j].end, S[k].end) - max(S[j].start, S[k].start)
                if overlap > 0:
                    overlaps += 1
        if overlaps == 0:
            ret.append(S[j])
    return ret


def find_nonoverlapping(segments, L):
    segments.sort(key=lambda x: (x.start, -x.end))
    # draw_segments(segments, L)

    S = segments
    n = len(S)
    j = 0
    k = 1
    max_end = 0
    result = []
    while j < n:
        # print("LOOP MID SEG:", S[j], "\tmax_end = ", max_end)
        next_start = S[j + 1].start if j < n - 1 else L
        if max_end <= S[j].start and S[j].end <= next_start:
            # print("NON OVERLAP", S[j])
            result.append(S[j])
        max_end = max(max_end, S[j].end)
        while k < n and S[k].end <= S[j].end:
            # print("SKIPPING", S[k])
            k += 1
        j = k
        k += 1
    return result


def find_identical_overlaps(segments, L):
    segments.sort(key=lambda x: (x.start, -x.end))
    draw_segments(segments, L)

    S = segments
    n = len(segments)
    j = 0
    k = 1
    result = []
    while j < n:
        equal = [S[j]]
        while k < n and S[j].start == S[k].start and S[j].end == S[k].end:
            equal.append(S[k])
            k += 1
        if len(equal) > 1:
            print("EQUAL:", equal)
        result.append(equal[0])
        j = k
        k += 1
    return result

def pairwise_find_max_overlap(segments, L):

#     for seg in segments:
#         print(seg.value, seg.start, seg.end, sep="\t")
#     draw_segments(segments, L)

    n = len(segments)
    max_overlap = 0
    max_overlap_segs = None
    for j in range(n):
        seg_j = segments[j]
        for k in range(j + 1, n):
            seg_k = segments[k]
            overlap = min(seg_j.end, seg_k.end) - max(seg_j.start, seg_k.start)
            # print("compare seg ", seg_j, seg_k, ":", overlap)
            if overlap > max_overlap:
                max_overlap = overlap
                max_overlap_segs = seg_j, seg_k
    # print("max overlap = ", max_overlap)
    # print("max overlap segs = ", max_overlap_segs)
    return max_overlap


def find_max_overlap(segments, L):
    segments.sort(key=lambda x: (x.start, -x.end))

    for seg in segments:
        print(seg.value, seg.start, seg.end, sep="\t")
    draw_segments(segments, L)

    S = segments
    n = len(segments)
    j = 0
    k = 1
    max_intersection = -1
    max_intersection_segs = []
    while True:
        # print("seg", j, S[j])
        while k < n and S[k].end <= S[j].end:
            intersection = S[k].end - S[k].start
            if intersection > max_intersection:
                max_intersection = intersection
                max_intersection_segs = [[j, k]]
            elif intersection == max_intersection:
                max_intersection_segs.append((j, k))
            k += 1
        if k == n:
            break
        intersection = S[j].end - S[k].start
        if intersection > max_intersection:
            max_intersection = intersection
            max_intersection_segs = [(j, k)]
        elif intersection == max_intersection:
            max_intersection_segs.append((j, k))
        j = k
        k += 1
    print("max_intersection = ", max_intersection)
    print("max_intersection_segs = ")
    for j, k in max_intersection_segs:
        print("\t", S[j], S[k])
    return max_intersection

#     out_queue = [(L + 1, None)]
#     max_end = -1

#     for in_seg in segments:
#         while out_queue[0][0] <= in_seg.start:
#             _, out_seg = heapq.heappop(out_queue)
#             print("out_seg = ", out_seg)
#         print("in_seg  = ", in_seg)
#         max_end = max(max_end, in_seg.end)
#         if len(out_queue) > 1:
#             end = out_queue[0][0]
#             # print("max overlap:", in_seg.start, end)
#         heapq.heappush(out_queue, (in_seg.end, in_seg))
#     while len(out_queue) > 1:
#         _, out_seg = heapq.heappop(out_queue)
#         print("out_seg = ", out_seg)


def trim_segments(segments, L):
    # partial implementation of trimming leading and trailing segments from
    # the set.

    segments.sort(key=lambda x: x.start)

    for seg in segments:
        print(seg.value, seg.start, seg.end, sep="\t")
    draw_segments(segments, L)

    out_queue = [(L + 1, None)]
    processed_segments = []

    prev_in_seg = None
    for in_seg in segments:
        while out_queue[0][0] <= in_seg.start:
            _, out_seg = heapq.heappop(out_queue)
            print("out_seg = ", out_seg)
            print("prev_in_seg = ", prev_in_seg)
            if len(out_queue) == 1 and out_seg.end <= prev_in_seg.end:
                print("SEG DONE")
            else:
                processed_segments.append(out_seg)
        if len(out_queue) == 2:
            print("LEADING TRIM:", prev_in_seg)
        print("in_seg  = ", in_seg)
        heapq.heappush(out_queue, (in_seg.end, in_seg))
        prev_in_seg = in_seg
    while len(out_queue) > 1:
        _, out_seg = heapq.heappop(out_queue)
        print("out_seg = ", out_seg)
        processed_segments.append(out_seg)
    return processed_segments

    # n = len(segments)
    # I = sorted(range(n), key=lambda j: segments[j].start)
    # O = sorted(range(n), key=lambda j: segments[j].end)
    # completed = []

    # print("I = ", I)
    # print("O = ", O)
    # k = 0
    # c = 0
    # for j in range(n):
    #     while k < n and segments[O[k]].end <= segments[I[j]].start:
    #         print("c = ", c, "pop ", segments[O[k]])
    #         # if c == 1:
    #         #     print("COMPLETED", segments[O[k]])
    #         k += 1
    #         c -= 1
    #     if c == 1 and segments[I[j - 1]].start != segments[I[j]].start:
    #         print("TRIM FRONT:", segments[I[j - 1]], segments[I[j]].start)
    #         segments[I[j - 1]].start = segments[I[j]].start
    #     print("c = ", c, "push", segments[I[j]])
    #     c += 1
    # while k < n:
    #     print("c = ", c, "pop ", segments[O[k]])
    #     k += 1
    #     c -= 1

    # print("Completed:")
    # for seg in completed:
    #     print(seg.value, seg.start, seg.end, sep="\t")
    # draw_segments(completed, L)

    return segments



def build_ancestors_dev(n, L, seed):

    ts = msprime.simulate(
        n, length=L, recombination_rate=1e-8, mutation_rate=1e-8,
        Ne=10**4, random_seed=seed)
    print("num_sites = ", ts.num_sites)
    position = [site.position for site in ts.sites()]
    S = np.zeros((ts.sample_size, ts.num_sites), dtype="i1")
    for variant in ts.variants():
        S[:, variant.index] = variant.genotypes

    # builder = _tsinfer.AncestorBuilder(S, position)
    builder = tsinfer.AncestorBuilder(S, position)
    store_builder = _tsinfer.AncestorStoreBuilder(
        builder.num_sites, builder.num_sites * 8192)

    for frequency_class, focal_sites in builder.get_frequency_classes():

        print(frequency_class, focal_sites)
        patterns = collections.defaultdict(list)
        for focal_site in focal_sites:
            site_pattern = tuple(S[:,focal_site])
            patterns[site_pattern].append(focal_site)
        num_ancestors = len(patterns)
        A = np.zeros((num_ancestors, builder.num_sites), dtype=np.int8)
        p = np.zeros(num_ancestors, dtype=np.uint32)
        for j, sites in enumerate(patterns.values()):
            builder.make_ancestor(sites, A[j, :])
        _tsinfer.sort_ancestors(A, p)
        for j in num_ancestors:
            store_builder.add(A[index, :])


def load_ancestors_dev(filename):

    with h5py.File(filename, "r") as f:
        sites = f["sites"]
        segments = f["segments"]
        ancestors = f["ancestors"]
        store = tsinfer.AncestorStore(
            position=sites["position"],
            site=segments["site"],
            start=segments["start"],
            end=segments["end"],
            state=segments["state"],
            focal_site=ancestors["focal_site"][:])
        samples = f["samples"]
        S = samples["haplotypes"][()]

    mutation_rate = 0.01
    # print(store.num_sites, store.num_ancestors)
    ancestor_ids = list(range(1, store.num_ancestors))
    # matcher = _tsinfer.AncestorMatcher(store, 0.01)
    matcher = tsinfer.AncestorMatcher(store, 1e-8)
    ts_builder = tsinfer.TreeSequenceBuilder(
            store.num_sites, S.shape[0], store.num_ancestors)

    # traceback = _tsinfer.Traceback(store, 2**10)
    traceback = tsinfer.Traceback(store)
    h = np.zeros(store.num_sites, dtype=np.int8)
    P = np.zeros(store.num_sites, dtype=np.int32)
    M = np.zeros(store.num_sites, dtype=np.uint32)

    # store.print_state()

    for ancestor_id in ancestor_ids:
        start_site, end_site, num_older_ancestors, focal_sites = store.get_ancestor(ancestor_id, h)
        # print(start_site, focal_site, end_site)
        # a = "".join(str(x) if x != -1 else '*' for x in h)
        # print(ancestor_id, "\t", a)
        best_match = matcher.best_path(
            ancestor_id, h, start_site, end_site, focal_site, 0, traceback)
        # print("best_match = ", best_match)
        traceback.run_build_ts(
            h, start_site, end_site, best_match, ts_builder, ancestor_id)
        # print("traceback", traceback)
        traceback.reset()
        # print()
        # assert num_mutations == 1

    # print("MATCHING SAMPLES")

    for j, h in enumerate(S):
        sample_id = j + store.num_ancestors
        # a = "".join(str(x) if x != -1 else '*' for x in h)
        # print(sample_id, "\t", a)
        best_match = matcher.best_path(
            store.num_ancestors, h, 0, store.num_sites, -1, mutation_rate, traceback)
        # print("best_match = ", best_match)
        num_mutations = traceback.run_build_ts(
            h, 0, store.num_sites, best_match, ts_builder, sample_id)
        # print("traceback", traceback)
        traceback.reset()
        # print()
        # assert num_mutations == 1

    # ts_builder.print_state()
    tsp = ts_builder.finalise()
    recurrent_mutations = 0
    back_mutations = 0
    for site in tsp.sites():
        # print(site)
        assert site.ancestral_state == '0'
        recurrent_mutations += (len(site.mutations) > 1)
        for mut in site.mutations:
            back_mutations += mut.derived_state == '0'
    print("recurrent muts    :", recurrent_mutations)
    print("back      muts    :", back_mutations)
    Sp = np.zeros((tsp.sample_size, tsp.num_sites), dtype="i1")
    for variant in tsp.variants():
        Sp[:, variant.index] = variant.genotypes
    assert np.all(Sp == S)
    # print("S = ")
    # print(S)
    # print("~Sp = ")
    # print(Sp)
    # print(Sp == S)
    tsp = tsp.simplify()
    # Need to compare on the haplotypes here because we might have a
    # ancestral state of 1 after simplify.
    H = list(tsp.haplotypes())
    for j in range(S.shape[0]):
        assert "".join(map(str, S[j])) == H[j]

    # for variant in tsp.variants():
    #     Sp[:, variant.index] = variant.genotypes
    # assert np.all(Sp == S)
    # tsp.dump("back-mutations-error.hdf5")



def compress_ancestors(filename):

    with h5py.File(filename, "r") as f:
        sites = f["sites"]
        segments = f["segments"]
        store = _tsinfer.AncestorStore(
            num_sites=sites["position"].shape[0],
            site=segments["site"],
            start=segments["start"],
            end=segments["end"],
            state=segments["state"])
        samples = f["samples"]
        S = samples["haplotypes"][()]

    # print(store.num_sites, store.num_ancestors)
    print(store)
    for l in range(store.num_sites):
        print(l, ":", store.get_site(l))

    A = np.zeros((store.num_ancestors, store.num_sites), dtype=np.int8) - 1
    for l in range(store.num_sites):
        for start, end, value in store.get_site(l):
            A[start:end, l] = value
    for a in A:
        a = "".join(str(x) if x != -1 else '*' for x in a)
        print(a)



def make_errors(v, p):
    """
    For each sample an error occurs with probability p. Errors are generated by
    sampling values from the stationary distribution, that is, if we have an
    allele frequency of f, a 1 is emitted with probability f and a
    0 with probability 1 - f. Thus, there is a possibility that an 'error'
    will in fact result in the same value.
    """
    w = np.copy(v)
    if p > 0:
        m = v.shape[0]
        frequency = np.sum(v) / m
        # Randomly choose samples with probability p
        samples = np.where(np.random.random(m) < p)[0]
        # Generate observations from the stationary distribution.
        errors = (np.random.random(samples.shape[0]) < frequency).astype(int)
        w[samples] = errors
    return w

def generate_samples(ts, error_p):
    """
    Returns samples with a bits flipped with a specified probability.

    Rejects any variants that result in a fixed column.
    """
    S = np.zeros((ts.sample_size, ts.num_mutations), dtype=np.int8)
    for variant in ts.variants():
        done = False
        # Reject any columns that have no 1s or no zeros
        while not done:
            S[:,variant.index] = make_errors(variant.genotypes, error_p)
            s = np.sum(S[:, variant.index])
            done = 0 < s < ts.sample_size
    return S


def sort_ancestor_slice(A, p, start, end, sort_order, depth=0):
    n = end - start
    if n > 1:
        # print("  " * depth, "Sort Ancestor slice:", start, ":", end, sep="")
        # print("  " * depth, "p = ", p, sep="")
        m = A.shape[1]
        max_segment_breaks = 0
        sort_site = -1
        for l in range(m):
            col = A[p[start:end], l]
            segment_breaks = 0
            for j in range(n):
                if j < n - 1:
                    if sort_order == 0:
                        if col[j] > col[j + 1]:
                            segment_breaks += 1
                    else:
                        if col[j] <= col[j + 1]:
                            segment_breaks += 1
            # if segment_breaks > 1:
            #     print("col = ", col, "segment_breaks = ", segment_breaks)
            if segment_breaks > max_segment_breaks:
                max_segment_breaks = segment_breaks
                sort_site = l
        if max_segment_breaks > 1:
            # print("sort_site = ", sort_site)
            # # print("A = ", A[p[start: end], sort_site])
            sorting = np.argsort(A[p[start: end], sort_site])
            if sort_order == 1:
                sorting = sorting[::-1]
            # print("sorting = ", sorting, sorting.dtype)
            # print(p)
            # print(p[sorting])
            p[start: end] = p[start + sorting]
            # print("after", p)
            assert np.all(np.unique(p) == np.arange(p.shape[0]))
            # recursively sort within these partitions.
            for j in range(start, end - 1):
                # print(depth * "  ", "testing:", j, A[p[j], sort_site],  A[p[j + 1], sort_site])
                if A[p[j], sort_site] != A[p[j + 1], sort_site]:
                    sort_ancestor_slice(A, p, start, j + 1, sort_order, depth + 1)
                    start = j + 1
                    # print(depth * " ", "start = ", start)


def sort_ancestors(A, p, sort_order):
    """
    Sorts the specified array of ancestors to maximise the effectiveness
    of the run length encoding.
    """
    n, m = A.shape
    p[:] = np.arange(n, dtype=int)
    # print("BEFORE")
    # for j in range(n):
    #     a = "".join(str(x) if x != -1 else '*' for x in A[p[j],:])
    #     print(j, "\t", a)
    sort_ancestor_slice(A, p, 0, n, sort_order, 0)
    # print("AFTER")
    # for j in range(n):
    #     a = "".join(str(x) if x != -1 else '*' for x in A[p[j], :])
    #     print(j, "\t", a)


def build_ancestors(n, L, seed):

    ts = msprime.simulate(
        n, length=L, recombination_rate=1e-8, mutation_rate=1e-8,
        Ne=10**4, random_seed=seed)
    print("num_sites = ", ts.num_sites)
    # print("simulation done, num_sites = ", ts.num_sites)

    # ts.dump(filename.split(".")[0] + ".ts.hdf5")

    position = [site.position for site in ts.sites()]

    S = np.zeros((ts.sample_size, ts.num_sites), dtype="i1")
    for variant in ts.variants():
        S[:, variant.index] = variant.genotypes
    np.random.seed(seed)
    # S = generate_samples(ts, 0.01)

    builder = _tsinfer.AncestorBuilder(S, position)
    store_builder = _tsinfer.AncestorStoreBuilder(
        builder.num_sites, builder.num_sites * 8192)
    num_threads = 20

    def build_frequency_class(work):
        frequency, focal_sites = work
        num_ancestors = len(focal_sites)
        A = np.zeros((num_ancestors, builder.num_sites), dtype=np.int8)
        p = np.zeros(num_ancestors, dtype=np.uint32)
        # print("frequency:", frequency, "sites = ", focal_sites)
        for j, focal_site in enumerate(focal_sites):
            builder.make_ancestor(focal_site, A[j, :])
        _tsinfer.sort_ancestors(A, p)
        # p = np.arange(num_ancestors, dtype=np.uint32)
        return frequency, focal_sites, A, p

    # TODO make these numpy arrays
    ancestor_focal_site = [-1]
    ancestor_frequency = [0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        for result in executor.map(build_frequency_class, builder.get_frequency_classes()):
            frequency, focal_sites, A, p = result
            for index in p:
                # print("adding:", A[index, :], frequency, focal_sites[index])
                # TODO add in the focal site informatino for matching on
                # ancestors.
                store_builder.add(A[index, :])
                ancestor_focal_site.append(focal_sites[index])
                ancestor_frequency.append(frequency)

    N = store_builder.total_segments
    site = np.zeros(N, dtype=np.uint32)
    start = np.zeros(N, dtype=np.int32)
    end = np.zeros(N, dtype=np.int32)
    state = np.zeros(N, dtype=np.int8)
    store_builder.dump_segments(site, start, end, state)
    with h5py.File(filename, "w") as f:
        g = f.create_group("segments")
        g.create_dataset("site", data=site)
        g.create_dataset("start", data=start)
        g.create_dataset("end", data=end)
        g.create_dataset("state", data=state)
        g = f.create_group("sites")
        g.create_dataset("position", data=position)
        g = f.create_group("samples")
        g.create_dataset("haplotypes", data=S)
        g = f.create_group("ancestors")
        g.create_dataset("frequency", data=ancestor_frequency, dtype=np.int32)
        g.create_dataset("focal_site", data=ancestor_focal_site, dtype=np.uint32)

    store = _tsinfer.AncestorStore(
        position=position, focal_site=ancestor_focal_site,
        site=site, start=start, end=end, state=state)

    print("num sites        :", store.num_sites)
    print("num ancestors    :", store.num_ancestors)
    print("max_segments     :", store.max_num_site_segments)
    print("mean_segments    :", store.total_segments / store.num_sites)
    print("Memory           :", humanize.naturalsize(store.total_memory))
    print("Uncompressed     :", humanize.naturalsize(store.num_ancestors * store.num_sites))
    print("Sample memory    :", humanize.naturalsize(S.nbytes))

def load_ancestors(filename, show_progress=True, num_threads=1):

    with h5py.File(filename, "r") as f:
        sites = f["sites"]
        segments = f["segments"]
        ancestors = f["ancestors"]
        store = _tsinfer.AncestorStore(
            position=sites["position"],
            focal_site=ancestors["focal_site"],
            site=segments["site"],
            start=segments["start"],
            end=segments["end"],
            state=segments["state"])
        samples = f["samples"]
        S = samples["haplotypes"][()]

    print("pid              :", os.getpid())
    print("num sites        :", store.num_sites)
    print("num ancestors    :", store.num_ancestors)
    print("max_segments     :", store.max_num_site_segments)
    print("mean_segments    :", store.total_segments / store.num_sites)
    print("Memory           :", humanize.naturalsize(store.total_memory))
    print("Uncompressed     :", humanize.naturalsize(store.num_ancestors * store.num_sites))

    num_samples = S.shape[0]
    tree_sequence_builder = _tsinfer.TreeSequenceBuilder(store, num_samples);
    recombination_rate = 1e-8
    error_rate = 1e-20
    method = "C"
    tsinfer.match_ancestors(
        store, recombination_rate, tree_sequence_builder, method=method,
        num_threads=num_threads)
    tsinfer.match_samples(
        store, S, recombination_rate, error_rate, tree_sequence_builder,
        method=method, num_threads=num_threads)
    ts = tsinfer.finalise_tree_sequence(num_samples, store, tree_sequence_builder)

    ts = ts.simplify()
    ts.dump(filename.split(".")[0] + ".inferred_ts.hdf5")

    memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    print("RAM              :", humanize.naturalsize(memory))

    for j, h in enumerate(ts.haplotypes()):
        assert "".join(map(str, S[j])) == h

    # duration_cpu = time.clock() - before_cpu
    # duration_wall = time.time() - before_wall
    # print("Copying CPU time :", humanize.naturaldelta(duration_cpu))
    # print("Copying wall time:", humanize.naturaldelta(duration_wall))

def new_segments(n, L, seed, num_threads=10, method="C"):

    np.set_printoptions(linewidth=2000)
    np.set_printoptions(threshold=20000)
    np.random.seed(seed)
    random.seed(seed)

    ts = msprime.simulate(
        n, length=L, recombination_rate=0.5, mutation_rate=1, random_seed=seed)
    if ts.num_sites == 0:
        print("zero sites; skipping")
        return
    positions = np.array([site.position for site in ts.sites()])
    # S = generate_samples(ts, 0.01)
    S = generate_samples(ts, 0)

    tsp = tsinfer.infer(S, positions, L, 1e-9, 1e-50,
            num_threads=num_threads, method=method)
    new_positions = np.array([site.position for site in tsp.sites()])
    assert np.all(new_positions == positions)

    Sp = np.zeros((tsp.sample_size, tsp.num_sites), dtype="i1")
    for variant in tsp.variants():
        Sp[:, variant.index] = variant.genotypes
    #print(S,np.sum(S))
    #print()
    #print(Sp,np.sum(Sp))
    assert np.all(Sp == S)

    # for t in tsp.trees():
    #     print(t.interval, t)
    # for site in tsp.sites():
    #     if len(site.mutations) > 1:
    #         print("Recurrent mutation")

    ts_simplified = tsp.simplify()
    # Need to compare on the haplotypes here because we might have a
    # ancestral state of 1 after simplify.
    H = list(tsp.haplotypes())
    for j in range(S.shape[0]):
        assert "".join(map(str, S[j])) == H[j]


def export_samples(n, L, seed):

    ts = msprime.simulate(
        n, length=L, recombination_rate=0.5, mutation_rate=1, random_seed=seed)
    print("num_sites = ", ts.num_sites)
    with open("tmp__NOBACKUP__/samples.txt", "w") as out:
        for variant in ts.variants():
            print(variant.position, "".join(map(str, variant.genotypes)), sep="\t", file=out)




def compare_timings(n, L, seed):
    ts = msprime.simulate(
        n, length=L, recombination_rate=0.5, mutation_rate=1, random_seed=seed)
    if ts.num_sites == 0:
        print("zero sites; skipping")
        return
    S = np.zeros((ts.sample_size, ts.num_sites), dtype="i1")
    for variant in ts.variants():
        S[:, variant.index] = variant.genotypes

    total_matching_time_new = 0
    # Inline the code here so we can time it.
    samples = S
    num_samples, num_sites = samples.shape
    builder = tsinfer.AncestorBuilder(samples)
    matcher = _tsinfer.AncestorMatcher(num_sites)
    num_ancestors = builder.num_ancestors
    # tree_sequence_builder = TreeSequenceBuilder(num_samples, num_ancestors, num_sites)
    tree_sequence_builder = tsinfer.TreeSequenceBuilder(num_samples, num_ancestors, num_sites)

    A = np.zeros(num_sites, dtype=np.int8)
    P = np.zeros(num_sites, dtype=np.int32)
    M = np.zeros(num_sites, dtype=np.uint32)
    for j, A in enumerate(builder.build_all_ancestors()):
        before = time.clock()
        num_mutations = matcher.best_path(A, P, M, 0.01, 1e-200)
        total_matching_time_new += time.clock() - before
        # print(A)
        # print(P)
        # print("num_mutations = ", num_mutations, M[:num_mutations])
        assert num_mutations == 1
        # assert M[0] == focal_site
        matcher.add(A)
        tree_sequence_builder.add_path(j + 1, P, A, M[:num_mutations])
    # tree_sequence_builder.print_state()

    for j in range(num_samples):
        before = time.clock()
        num_mutations = matcher.best_path(samples[j], P, M, 0.01, 1e-200)
        total_matching_time_new += time.clock() - before
        u = num_ancestors + j + 1
        tree_sequence_builder.add_path(u, P, samples[j], M[:num_mutations])
    # tree_sequence_builder.print_state()
    tsp = tree_sequence_builder.finalise()

    Sp = np.zeros((tsp.sample_size, tsp.num_sites), dtype="i1")
    for variant in tsp.variants():
        Sp[:, variant.index] = variant.genotypes
    assert np.all(Sp == S)

    S = S.astype(np.uint8)
    panel = tsinfer.ReferencePanel(
        S, [site.position for site in ts.sites()], ts.sequence_length,
        rho=0.001, algorithm="c")
    before = time.clock()
    P, mutations = panel.infer_paths(num_workers=1)
    total_matching_time_old = time.clock() - before
    ts_new = panel.convert_records(P, mutations)
    Sp = np.zeros((ts_new.sample_size, ts_new.num_sites), dtype="u1")
    for variant in ts_new.variants():
        Sp[:, variant.index] = variant.genotypes
    assert np.all(Sp == S)
    print(n, L, total_matching_time_old, total_matching_time_new, sep="\t")

def ancestor_gap_density(n, L, seed):
    ts = msprime.simulate(
        n, length=L, recombination_rate=0.5, mutation_rate=1, random_seed=seed)
    if ts.num_sites == 0:
        print("zero sites; skipping")
        return
    S = np.zeros((ts.sample_size, ts.num_sites), dtype="i1")
    for variant in ts.variants():
        S[:, variant.index] = variant.genotypes

    samples = S
    num_samples, num_sites = samples.shape
    builder = tsinfer.AncestorBuilder(samples)
    # builder.print_state()
    matcher = tsinfer.AncestorMatcher(num_sites)
    num_ancestors = builder.num_ancestors

    # A = np.zeros(num_sites, dtype=np.int8)
    P = np.zeros(num_sites, dtype=np.int32)
    M = np.zeros(num_sites, dtype=np.uint32)
    for A in builder.build_all_ancestors():
        matcher.add(A)

#     for j in range(builder.num_ancestors):
#         focal_site = builder.site_order[j]
#         builder.build(j, A)
#         matcher.add(A)
    # matcher.print_state()
#     builder.print_state()
#     builder.print_all_ancestors()

    total_segments = np.zeros(ts.num_sites)
    total_blank_segments = np.zeros(ts.num_sites)
    total_blank_segments_distance = 0

    for l in range(matcher.num_sites):
        seg = matcher.sites_head[l]
        while seg is not None:
            # print(seg.start, seg.end, seg.value)
            total_segments[l] += 1
            if seg.value == -1:
                total_blank_segments[l] += 1
                total_blank_segments_distance += seg.end - seg.start
            seg = seg.next

    return {
        "n": n, "L": L,
        "num_sites":matcher.num_sites,

        "num_ancestors": matcher.num_ancestors,
        "mean_total_segments": np.mean(total_segments),
        "mean_blank_segments": np.mean(total_blank_segments),
        "total_blank_fraction": total_blank_segments_distance / (num_sites * num_ancestors)
    }

def site_set_stats(n, L, seed):
    ts = msprime.simulate(
        n, length=L, recombination_rate=1e-8, mutation_rate=1e-8,
        Ne=10**4, random_seed=seed)
    # print("n          = ", n)
    # print("L          = ", L / 10**6, "Mb")
    # print("sites      = ", ts.num_sites)

    positions = [site.position for site in ts.sites()]
    S = np.zeros((ts.sample_size, ts.num_sites), dtype="i1")
    for variant in ts.variants():
        S[:, variant.index] = variant.genotypes

    num_samples, num_sites = S.shape
    builder = _tsinfer.AncestorBuilder(S, positions)
    store_builder = _tsinfer.AncestorStoreBuilder(
            builder.num_sites, 8192 * builder.num_sites)
    frequency_classes = builder.get_frequency_classes()
    num_ancestors = 1 + sum(len(sites) for _, sites in frequency_classes)
    # print("ancestors  = ", num_ancestors)

    A = np.zeros((num_ancestors, num_sites), dtype=np.int8)
    j = 1
    for frequency, focal_sites in builder.get_frequency_classes():
        for focal_site in focal_sites:
            assert np.sum(S[:, focal_site]) == frequency

            builder.make_ancestor(focal_site, A[j, :])
            j += 1
    sparsity = np.sum(A == -1) / (num_ancestors * num_sites)
    # print("sparsity   = ", sparsity)
    last_zeros = set()
    last_ones = set()
    last_zeros = set(np.where(A[:, 0] == 0)[0])
    last_ones = set(np.where(A[:, 0] == 1)[0])
    total_diffs = np.zeros(num_sites)
    for l in range(1, num_sites):
        zeros = set(np.where(A[:, l] == 0)[0])
        ones = set(np.where(A[:, l] == 1)[0])
        print("l = ", l)
        print("zeros = ", len(zeros), "::\t", zeros)
        print("ones  = ", len(ones), "::\t", ones)
        zero_zero_diff = zeros ^ last_zeros
        zero_one_diff = ones ^ last_zeros
        if len(zero_one_diff) < len(zero_zero_diff):
            # print("Swapping", len(zero_one_diff), len(zero_zero_diff))
            zeros = set(np.where(A[:, l] == 1)[0])
            ones = set(np.where(A[:, l] == 0)[0])
        zeros_diff = zeros ^ last_zeros
        ones_diff = ones ^ last_ones

        total_diffs[l] = len(zeros_diff) + len(ones_diff)
        print("total diffs = ", total_diffs[l])
        last_zeros = zeros
        last_ones = ones
    # print("mean diffs = ", np.mean(total_diffs))
    return {
        "n": n,
        "L": L,
        "sites": ts.num_sites,
        "ancestors": num_ancestors,
        "sparsity": sparsity,
        "mean_diffs": np.mean(total_diffs)
    }

def rle(inarray):
        """ run length encoding. Partial credit to R rle function.
            Multi datatype arrays catered for including non Numpy
            returns: tuple (runlengths, startpositions, values) """
        ia = np.array(inarray)                  # force numpy
        n = len(ia)
        if n == 0:
            return (None, None, None)
        else:
            y = np.array(ia[1:] != ia[:-1])     # pairwise unequal (string safe)
            i = np.append(np.where(y), n - 1)   # must include last element posi
            z = np.diff(np.append(-1, i))       # run lengths
            p = np.cumsum(np.append(0, z))[:-1] # positions
            return {'length':z, 'start':p, 'value':ia[i]}

class Visualiser(object):

    def __init__(self, width, num_sites, font_size=12):
        self.drawing = svgwrite.Drawing(width=width, debug=True)
        self.num_sites = num_sites
        self.scale = width / (num_sites + 1)
        self.font_size = font_size
        # We need this to make sure the coordinate system works properly.
        # Must be a better way to do it!
        self.drawing.add(self.drawing.rect(
            (0, 0), (width, self.scale),
            stroke="white", fill="white"))
        if font_size is not None:
            self.text_offset = self.font_size / 2 # TODO improve this!
            self.labels = self.drawing.add(
                self.drawing.g(font_size=font_size, text_anchor="middle"))
        stroke = "lightgray"
        self.focal_boxes = self.drawing.add(
                self.drawing.g(fill="red", stroke=stroke))
        self.one_boxes = self.drawing.add(
                self.drawing.g(fill="salmon", stroke=stroke))
        self.zero_boxes = self.drawing.add(
                self.drawing.g(fill="blue", stroke=stroke))
        self.missing_boxes = self.drawing.add(
                self.drawing.g(fill="white", stroke=stroke))
        self.current_row = 0
        self.label_map = {}

    def add_site_coordinates(self):
        if self.font_size is not None:
            for k in range(self.num_sites):
                coord = (
                    (k + 1) * self.scale + self.scale / 2,
                    self.current_row + self.scale / 2)
                self.labels.add(self.drawing.text(str(k), coord, dy=[self.text_offset]))
        self.current_row += 1

    def add_row(self, a, row_label=None, focal=[]):
        j = self.current_row
        self.label_map[row_label] = j
        if self.font_size is not None and row_label is not None:
            coord = (self.scale / 2, j * self.scale + self.scale / 2)
            self.labels.add(
                self.drawing.text(str(row_label), coord, dy=[self.text_offset]))
        for k in range(self.num_sites):
            corner = ((k + 1) * self.scale, j * self.scale)
            if a[k] == 0:
                self.zero_boxes.add(self.drawing.rect(corner, (self.scale, self.scale)))
            elif a[k] == -1:
                self.missing_boxes.add(self.drawing.rect(corner, (self.scale, self.scale)))
            else:
                if k in focal:
                    self.focal_boxes.add(self.drawing.rect(corner, (self.scale, self.scale)))
                else:
                    self.one_boxes.add(self.drawing.rect(corner, (self.scale, self.scale)))
        self.current_row += 1

    def add_intensity_row(self, d, row_label=None):
        j = self.current_row
        if self.font_size is not None and row_label is not None:
            coord = (self.scale / 2, j * self.scale + self.scale / 2)
            self.labels.add(
                self.drawing.text(str(row_label), coord, dy=[self.text_offset]))
        bottom = colour.Color("white")
        colours = list(bottom.range_to(colour.Color("black"), 10))
        bins = np.linspace(0, 1, 10)
        a = np.digitize(d, bins) - 1
        for k in range(self.num_sites):
            corner = ((k + 1) * self.scale, j * self.scale)
            self.drawing.add(self.drawing.rect(
                corner, (self.scale, self.scale), stroke="lightgrey",
                fill=colours[a[k]]))
        self.current_row += 1

    def add_separator(self):
        self.current_row += 1

    def show_path(self, label, path, fade_recents=True, copy_groups=None):
        """
        param copy_groups is only useful if there is the same ancestor on multiple rows
        """
        #highlight (darken) the cells we copied from
        for k in range(self.num_sites):
            rows = [path[k]] if copy_groups is None else copy_groups[path[k]]
            for r in rows:
                j = self.label_map[r]
                corner = ((k + 1) * self.scale, j * self.scale)
                self.drawing.add(self.drawing.rect(
                    corner, (self.scale, self.scale), stroke="lightgrey",
                    fill="black", opacity=0.6))

        if not fade_recents and label in self.label_map:
            # (slightly) highlight the current line
            row = self.label_map[label]
            corner = self.scale, row * self.scale
            self.drawing.add(self.drawing.rect(
                corner, ((self.scale * self.num_sites), self.scale),
                stroke="black", fill_opacity=0.2))

        elif fade_recents and label + 1 in self.label_map:
            #  fade out the more recent stuff
            row = self.label_map[label + 1]
            corner = self.scale, row * self.scale
            height = (self.current_row - row) * self.scale
            self.drawing.add(self.drawing.rect(
                corner, ((self.scale * self.num_sites), height),
                fill="white", opacity=0.8))

    def fade_row_false(self, bool_arr, label):
        row = self.label_map[label]
        runlengths = rle(bool_arr)
        height = self.scale
        for i in np.where(~runlengths['value'])[0]:
            corner = self.scale * (runlengths['start'][i]+1), row * self.scale
            self.drawing.add(self.drawing.rect(
                corner, ((self.scale * runlengths['length'][i]), height),
                fill="white", opacity=0.8))

    def save(self, filename):
        self.drawing.saveas(filename)


def visualise_ancestors(n, L, seed):

    np.set_printoptions(linewidth=2000)
    np.set_printoptions(threshold=20000)
    np.random.seed(seed)
    random.seed(seed)

    ts = msprime.simulate(
        n, length=L, recombination_rate=0.5, mutation_rate=1, random_seed=seed)
    if ts.num_sites == 0:
        print("zero sites; skipping")
        return
    positions = np.array([site.position for site in ts.sites()])
    S = np.zeros((ts.sample_size, ts.num_sites), dtype="i1")
    for variant in ts.variants():
        S[:, variant.index] = variant.genotypes
    frequency = np.sum(S, axis=0)

    store = tsinfer.build_ancestors(S, positions, method="P")
    visualiser = Visualiser(800, store.num_sites, font_size=16)
    visualiser.add_site_coordinates()
    visualiser.add_row(a, 0)
    a = np.zeros(store.num_sites, dtype=np.int8)
    last_frequency = 0
    for j in range(1, store.num_ancestors):
        start, end, num_older_ancestors, focal_sites= store.get_ancestor(j, a)
        if any(frequency[focal] != last_frequency for focal in focal_sites):
            visualiser.add_separator()
            last_frequency = frequency[focal]
        visualiser.add_row(a, j)

    visualiser.add_separator()
    j = store.num_ancestors
    for a in S:
        visualiser.add_row(a, j)
        j += 1

    visualiser.save("tmp.svg")


def draw_copying_density(ts, width, breaks):
    """
    Visualises the copying density of the specified tree sequence.
    """
    num_ancestors = ts.num_nodes - ts.sample_size
    D = np.zeros((num_ancestors, ts.num_sites), dtype=int)
    for e in ts.edgesets():
        # FIXME!!! This will break when we start outputting positions correctly!
        left = int(e.left)
        right = int(e.right)
        D[e.parent, left:right] = len(e.children)
    # Rescale D into 0/1
    D = D / np.max(D)

    visualiser = Visualiser(width, ts.num_sites, font_size=16)
    visualiser.add_site_coordinates()
    for j in range(num_ancestors):
        if j in breaks:
            visualiser.add_separator()
        visualiser.add_intensity_row(D[j], j)

    visualiser.save("intensity.svg")



def visualise_copying(n, L, seed):

    np.set_printoptions(linewidth=2000)
    np.set_printoptions(threshold=20000)
    np.random.seed(seed)
    random.seed(seed)

    ts = msprime.simulate(
        n, length=L, recombination_rate=0.5, mutation_rate=1, random_seed=seed)
    if ts.num_sites == 0:
        print("zero sites; skipping")
        return
    positions = np.array([site.position for site in ts.sites()])
    S = np.zeros((ts.sample_size, ts.num_sites), dtype="i1")
    for variant in ts.variants():
        S[:, variant.index] = variant.genotypes
    frequency = np.sum(S, axis=0)

    store = tsinfer.build_ancestors(S, positions, method="C")
    inferred_ts = tsinfer.infer(S, positions, L, 1e-6, 1e-200)

    last_frequency = 0
    breaks = set()
    a = np.zeros(store.num_sites, dtype=np.int8)
    for j in range(1, store.num_ancestors):
        start, end, num_older_ancestors, focal_sites = store.get_ancestor(j, a)
        if frequency[focal_sites[0]] != last_frequency:
            last_frequency = frequency[focal_sites[0]]
            breaks.add(j)

    visualiser = Visualiser(800, store.num_sites, font_size=16)
    visualiser.add_site_coordinates()
    a = np.zeros(store.num_sites, dtype=np.int8)
    visualiser.add_row(a, 0)
    for j in range(1, store.num_ancestors):
        if j in breaks:
            visualiser.add_separator()
        start, end, num_older_ancestors, focal_sites = store.get_ancestor(j, a)
        visualiser.add_row(a, j)

    N = store.num_ancestors + S.shape[0]
    P = np.zeros((N, store.num_sites), dtype=int) - 1
    site_index = {}
    for site in inferred_ts.sites():
        site_index[site.position] = site.index
    site_index[inferred_ts.sequence_length] = inferred_ts.num_sites
    site_index[0] = 0

    for e in inferred_ts.edgesets():
        for c in e.children:
            left = site_index[e.left]
            right = site_index[e.right]
            assert left < right
            P[c, left:right] = e.parent

#     visualiser.save("tmp.svg")

#     draw_copying_density(inferred_ts, 800, breaks)
    #make a map of which are actually used in the inferred ts
    locations = np.array([s.position for s in inferred_ts.sites()])
    used = np.zeros((store.num_ancestors, len(locations)),dtype=np.bool)
    #to do - this is a hack to get a row number for a node
    #it may not continue to work
    max_time = max([int(n.time) for n in inferred_ts.nodes()])
    rows_for_nodes = [max_time-int(n.time) for n in inferred_ts.nodes()]
    for es in inferred_ts.edgesets():
        used_variants = np.logical_and(es.left<=locations, locations<es.right)
        used[rows_for_nodes[es.parent], used_variants]=True

    for k in range(1, store.num_ancestors):
        #one file for each copied ancestor
        focal2row = {}
        visualiser = Visualiser(800, store.num_sites, font_size=9)
        big_visualiser = Visualiser(800, store.num_sites, font_size=9)

        visualiser.add_site_coordinates()
        big_visualiser.add_site_coordinates()

        a = np.zeros(store.num_sites, dtype=np.int8)

        visualiser.add_row(a, 0)
        big_visualiser.add_row(a, 0)

        for j in range(1, store.num_ancestors):
            if j in breaks:
                visualiser.add_separator()
                big_visualiser.add_separator()
            start, end, num_older_ancestors, focal_sites = store.get_ancestor(j, a)
            for f in focal_sites:
                focal2row[f]=j
                big_visualiser.add_row(a, j, focal_sites)
                big_visualiser.fade_row_false(used[j], j)
            visualiser.add_row(a, j, focal_sites)
            visualiser.fade_row_false(used[j], j)
        #highlight the path
        visualiser.show_path(k, P[k], False)
        big_visualiser.show_path(k, P[k], False)

        #add samples
        visualiser.add_separator()
        big_visualiser.add_separator()
        for j in range(S.shape[0]):
            visualiser.add_row(S[j],None,np.where(np.sum(S,0)==1)[0])
            big_visualiser.add_row(S[j],None,np.where(np.sum(S,0)==1)[0])
        print("Writing inferred ancestor copy plots", k)
        visualiser.save("tmp__NOBACKUP__/inferred_{}.svg".format(k))
        big_visualiser.save("tmp__NOBACKUP__/inferred_big_{}.svg".format(k))

    #visualize the true copying process, with real ancestral fragments
    #in the same order as in the inferred sequence.
    h, p = msprime_to_inference_matrices.make_ancestral_matrices(ts)
    freq_order, node_mutations = {}, {}
    for v in ts.variants():
        freq = np.sum(v.genotypes)
        for m in v.site.mutations:
            freq_order.setdefault(freq,[]).append({'node':m.node,'site':m.site, 'row':focal2row.get(m.site)})
            node_mutations.setdefault(m.node,[]).append(m.site)

    #for k,v in freq_order.items(): #print the list of ancestors output
    #    print(k,v)
    #    print()
    #exclude ancestors of singletons
    output_rows = [n for k in freq_order.keys() for n in freq_order[k] if k>1]
    output_rows.sort(key=operator.itemgetter('row'))
    freq_ordered_mutation_nodes = np.array([o['node'] for o in output_rows], dtype=np.int)
    #add the samples to the rows to keep
    keep_nodes = np.append(freq_ordered_mutation_nodes, range(ts.sample_size))
    H = h[keep_nodes,:]
    P, row_map = msprime_to_inference_matrices.relabel_copy_matrix(p, keep_nodes)
    groups = [row_map[n] for n in keep_nodes] + [[0]]
    visualiser = Visualiser(800, store.num_sites, font_size=9)
    visualiser.add_site_coordinates()
    a = np.zeros(store.num_sites, dtype=np.int8)
    visualiser.add_row(a, 0)
    visualiser.add_separator()
    row = 0
    for k in reversed(sorted(freq_order.keys())):
        if k>1:
            for j in freq_order[k]:
                visualiser.add_row(H[row,], keep_nodes[row], node_mutations[keep_nodes[row]])
                row += 1
            visualiser.add_separator()
    while row < H.shape[0]:
        visualiser.add_row(H[row,], keep_nodes[row], np.where(np.sum(H[-ts.sample_size:,],0)==1)[0])
        row += 1
    visualiser.save("tmp__NOBACKUP__/real.svg")

def run_large_infers():
    seed = 100
    n = 2000
    # n = 10
    for j in np.arange(10, 200, 10):
        print("n                :", n)
        print("L                :", j, "Mb")
        filename = "tmp__NOBACKUP__/n={}_L={}_original.hdf5".format(n, j)
        L = j * 10**6
        ts = msprime.simulate(
            n, length=L, recombination_rate=1e-8, mutation_rate=1e-8,
            Ne=10**4, random_seed=seed)
        print("sites            :", ts.num_sites)
        ts.dump(filename)
        positions = np.array([site.position for site in ts.sites()])
        S = generate_samples(ts, 0)
        before_cpu = time.clock()
        before_wall = time.time()
        ts_inferred = tsinfer.infer(
            S, positions, L, 1e-8, 1e-200, num_threads=20, method="C", show_progress=True)
        duration_cpu = time.clock() - before_cpu
        duration_wall = time.time() - before_wall
        filename = "tmp__NOBACKUP__/n={}_L={}_inferred.hdf5".format(n, j)
        ts_inferred.dump(filename)
        ts_simplified = ts_inferred.simplify()
        filename = "tmp__NOBACKUP__/n={}_L={}_simplified.hdf5".format(n, j)
        ts_simplified.dump(filename)
        memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        print("CPU time       :", humanize.naturaldelta(duration_cpu))
        print("wall time:     :", humanize.naturaldelta(duration_wall))
        print("RAM            :", humanize.naturalsize(memory))
        print()

def analyse_file(filename):
    ts = msprime.load(filename)

    num_children = np.zeros(ts.num_edgesets, dtype=np.int)
    for j, e in enumerate(ts.edgesets()):
        # print(e.left, e.right, e.parent, ts.time(e.parent), e.children, sep="\t")
        num_children[j] = len(e.children)

    print("total edgesets = ", ts.num_edgesets)
    print("non binary     = ", np.sum(num_children > 2))
    print("max children   = ", np.max(num_children))
    print("mean children  = ", np.mean(num_children))

    # for t in ts.trees():
    #     t.draw("tree_{}.svg".format(t.index), 4000, 4000)
    #     if t.index == 10:
    #         break

def draw_tree_for_position(pos, ts):
    """
    useful for debugging
    """
    for t in ts.trees():
        if t.get_interval()[0]<list(ts.sites())[pos].position and t.get_interval()[1]>list(ts.sites())[pos].position:
            t.draw("tmp__NOBACKUP__/tree_at_pos{}.svg".format(pos))




if __name__ == "__main__":

    np.set_printoptions(linewidth=20000)
    np.set_printoptions(threshold=200000)

    # for j in range(1, 100000):
    #     print(j)
    #     # new_segments(20, 200, j)
    #     new_segments(20, 20, j, num_threads=1, method="P")

    # new_segments(40, 50, 5)
    # new_segments(10, 10, 304, num_threads=1, method="P")

    # export_samples(10, 100, 304)


    # n = 10
    # for L in np.linspace(100, 1000, 10):
    #     compare_timings(n, L, 1)

    # d = ancestor_gap_density(20, 40, 1)

    # rows = []
    # n = 10
    # for L in np.linspace(10, 5000, 20):
    #     d = ancestor_gap_density(n, L, 2)
    #     rows.append(d)
    #     df = pd.DataFrame(rows)
    #     print(df)
    #     df.to_csv("gap-analysis.csv")

    # run_large_infers()
    # analyse_file("tmp__NOBACKUP__/n=1000_L=10_simplified.hdf5")

    # for j in range(1, 10000):
    # # for j in [4]:
    #     print(j, file=sys.stderr)
    #     filename = "tmp__NOBACKUP__/tmp-3.hdf5"
    #     load_ancestors(filename)
        # load_ancestors_dev(filename)

    #     filename = "tmp__NOBACKUP__/tmp2.hdf5"
    #     build_ancestors(10, 0.1 * 10**6, 3, filename)
    #     # compress_ancestors(filename)
    #     load_ancestors_dev(filename)

    # load_ancestors("tmp__NOBACKUP__/n=10_L=11.hdf5", num_threads=40)
    # load_ancestors("tmp__NOBACKUP__/n=10_L=121.hdf5")


    # d = site_set_stats(10, 50 * 10**6, 2)
    # rows = []
    # for n in [10, 100, 1000, 10000]:
    #     for l in range(1, 11):
    #         d = site_set_stats(n, l * 10 * 10**6, 2)
    #         rows.append(d)
    #         df = pd.DataFrame(rows)
    #         print(df)
    #         df.to_csv("diff-analysis.csv")

    # visualise_copying(8, 4, 5)
    # build_ancestors_dev(10, 10000, 3)
    for j in range(555550):
    # j = 1
        try:
            overlap_algorithm_dev(1, [(5 * k, 4 * k + 30) for k in range(30)], j, duplicate_proba=0)
        except Exception as e:
            print("FAIL:", j)
            raise e
