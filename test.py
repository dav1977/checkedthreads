#!/usr/bin/python
'''stuff we test:
* "hello" should work with all enabled schedulers and link against all single-scheduler libraries.
* "sleep" should sleep "quickly" with all enabled schedulers (partitioning test)
* random checker should find bugs.
* valgrind checker should find bugs.
'''
import os
import sys
import build
import commands

tests = 'bug.cpp'.split() # FIXME: 'nested.cpp grain.cpp acc.cpp bugs.cpp cancel.cpp sort.cpp'.split()

with_cpp = 'C++11' in build.enabled
with_pthreads = 'pthreads' in build.enabled
with_openmp = 'openmp' in build.enabled
with_tbb = 'tbb' in build.enabled

print '\nbuilding tests'

verbose = build.verbose
built = []
def buildtest(*args):
    built.append(build.buildtest(*args))

buildtest('hello_ct.c')
if with_pthreads: buildtest('hello_ct.c','_pthreads')
if with_openmp: buildtest('hello_ct.c','_openmp')

if with_cpp:
    buildtest('hello_ctx.cpp')
    if with_pthreads: buildtest('hello_ctx.cpp','_pthreads')
    if with_openmp: buildtest('hello_ctx.cpp','_openmp')
    if with_tbb: buildtest('hello_ctx.cpp','_tbb')

for test in tests:
    if test.endswith('.cpp') and not with_cpp:
        continue
    build.buildtest(test)

scheds = 'serial shuffle valgrind openmp tbb pthreads'.split()
# remove schedulers which we aren't configured to support
def lower(ls): return [s.lower() for s in ls]
scheds = [sched for sched in scheds if not (sched in lower(build.features) \
                                        and sched not in lower(build.enabled))]

failed = []
def fail(command):
    print ' ',command,'FAILED'
    failed.append(command)

def runtest(name,expected_status=0,expected_output=None,**env):
    envstr=' '.join(['%s=%s'%(n,v) for n,v in env.items()])
    command = 'env %s ./bin/%s'%(envstr,name)
    return runcommand(command,expected_status,expected_output)

def runcommand(command,expected_status=0,expected_output=None):
    if verbose:
        print ' ','running',command
    status,output = commands.getstatusoutput(command)
    if verbose>1:
        print '   ','\n    '.join(output.split('\n'))
    bad_status = status != expected_status and expected_status != None
    bad_output = output != expected_output and expected_output != None
    if bad_status or bad_output:
        fail(command)
    return status, output, command

print '\nrunning tests'

# hello: all builds should run, and all schedulers should be available in the "all-scheduler" build
hellos = [t for t in built if t.startswith('hello')]
hello_output = 'results: 0 3 6 ... 291 294 297'
for hello in hellos:
    runtest(hello,expected_output=hello_output)
for sched in scheds:
    sched_tests = []
    if with_cpp:
        sched_tests.append('hello_ctx')
    if sched != 'tbb':
        sched_tests.append('hello_ct')
    for sched_test in sched_tests:
        runtest(sched_test,expected_output=hello_output,CT_SCHED=sched)

# bug: one of the random orders should find the bug, with and without valgrind;
# the reverse order /shouldn't/ find the bug
s1, o1, c1 = runtest('bug',expected_status=None,CT_SCHED='shuffle')
s2, o2, c2 = runtest('bug',expected_status=None,CT_SCHED='shuffle',CT_RAND_REV=1)
if s1 == s2 or (s1 != 0 and s2 != 0):
    fail(c1)
    fail(c2)
elif verbose:
    print ' ','bug found when running one of the random orders'

# run bug under valgrind:
s1, o1, c1 = runcommand('env CT_SCHED=valgrind valgrind --tool=checkedthreads ./bin/bug',expected_status=None)
s2, o2, c2 = runcommand('env CT_SCHED=valgrind CT_RAND_REV=1 valgrind --tool=checkedthreads ./bin/bug',expected_status=None)
loc1='bug.cpp:16'
loc2='bug.cpp:18'
if not ((loc1 in o1 and loc2 in o2) or \
        (loc2 in o1 and loc1 in o2)):
    fail(c1)
    fail(c2)
elif verbose:
    print ' ','bug found when running either of the random orders'

if failed:
    print 'FAILED:'
    print '\n'.join(failed)
    sys.exit(1)
