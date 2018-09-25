# Yet another simple init

## Overview

This is one opinion what an `init` in Docker containers
should look like.

* Start one or more processes, our "children".

* Terminate when none of our children is running any longer.

* Stop the show whenever any of our children terminates,
  for whatever reason.

* Stop the show when we receive SIGTERM.

* Take care of orphans, that is, processes we did not start ourselves,
  but that terminated after their parent process.  Shrug shoulders and
  continue.

## Stop the show

When we stop the show, we simply send any of our children still alive
the SIGTERM signal.  We will then terminate as soon as none of our
children is running, or after a timeout of some 20 seconds, whichever
of the two comes first.

We do not restart.  We assume there's something in control upstairs,
outside the Docker container, that will decide whether to restart.
(This could be `systemd` or Kubernetes or Amazon ECS or whatever.)

## Do I need an `init`?

Maybe you don't.

If you answer "yes" to all of the following questions, you are fine
without an `init` and can instead run your target application as
process 1 of your Docker container:

* Your software does not produce orphan processes.

* You want to run a one-process application, not a few of them.

* That process has a signal handler for SIGTERM.

For the first condition, I had set up a "sidecar"-container that
allowed users to up- and download content via restricted `rsync`.  In
my particular setup, OpenSSL's `sshd` produces one orphan for each
connection that attempts to log in.  (`UsePrivilegeSeparation sandbox`
could potentially have played a role.)

For the last condition, it should be remarked that the standard Linux
behavior does not apply.  Normally, a process without a SIGTERM signal
handler will terminate when receiving that signal.  However, a process
1 in any Linux, including in a Docker container, will find itself
shielded from signals it does not handle, which is something the Linux
kernel does.

So, unless a handler for SIGKILL has been registered, this does
nothing:

     docker exec my_container kill -9 1

The container continues to run. (Even assuming you have the `kill`
command in your container.)  The non-ignorable signal is ignored.

For the "only one process" condition - this software and its author
are un-dogmatic about that one.  Sometimes, it is convenient to run
several processes in the same Docker container.  In my opinion, a
process is some implementation detail, a low-level building block, not
more important than a subroutine or software module.  Having two
should not mean that one of these processes has to take the
responsibility for the other one and become process 1.  That can be
delegated to a third process; a few lines of Python code should do the
trick.  In other words, if you want to be dogmatic against
multi-process containers, fine, have fun, but feel warmly invited to
go preach elsewhere.

The "orphans" are often a non-issue.  But there is some
fire-and-forget tactics which might produce them in numbers.  Not a
problem with a decent `init`, even a simple one like this.

## Tests

```
virtualenv -p $(which python3) virtualenv &&
. virtualenv/bin/activate &&
cd test && python -m unittest discover
```

The tests in their present form have known race conditions.
On my machine, they fail the first time after a reboot,
but rerunning immediately thereafter works.