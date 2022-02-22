import os, os.path, signal, subprocess, unittest

# Copyright 2018, 2020 Andreas Krüger, andreas.krueger@famsik.de
# 
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License. You may
# obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.

class YasinitTest(unittest.TestCase):

    IMAGE_TAG = 'python:3.10-bullseye'

    OVERHEAD_FOR_DOCKER = 3 # seconds
    SHUTDOWN_DURATION = 2   # seconds
    
    @classmethod
    def setUpClass(cls):
        tag_found = subprocess.run(['docker', 'image', 'ls', YasinitTest.IMAGE_TAG,
                                    '--format', '{{.Repository}}:{{.Tag}}'],
                                   universal_newlines = True,
                                   stdout = subprocess.PIPE, check = True).stdout.rstrip()
        if not YasinitTest.IMAGE_TAG == tag_found:
            subprocess.run(['docker', 'image', 'pull', YasinitTest.IMAGE_TAG],
                                   stdout = None, check = True)

    def run_docker(self, directory, cmd = [], stdout = None, stderr = None):
        pwd = os.getcwd()
        args = [
            'docker', 'run', '--rm',
            '--attach=STDOUT', '--attach=STDERR',
            '--volume={}/{}:/etc/yasinit'.format(pwd, directory),
            '--volume={}:/usr/local/bin/yasinit'.format(os.path.abspath('../yasinit')),
            '--entrypoint=/usr/local/bin/yasinit',
            YasinitTest.IMAGE_TAG
        ]
        if cmd:
            args[len(args):len(args)] = cmd
        return subprocess.Popen(args, stdin = subprocess.DEVNULL, stdout = stdout, stderr = stderr, universal_newlines = True)

    def test_normal_run_shutdown_from_outside(self):
        popen = self.run_docker('1', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        with self.assertRaises(subprocess.TimeoutExpired):
            (o, e) = popen.communicate(timeout = YasinitTest.OVERHEAD_FOR_DOCKER)
            print("ERROR: This should not happen:\n{}\n{}\n".format(e, o))
        popen.terminate()
        (stdout_data, stderr_data) = popen.communicate(timeout = YasinitTest.SHUTDOWN_DURATION)
        self.assertEqual('', stdout_data)
        self.assertIsNot(-1, stderr_data.find("Command ['/etc/yasinit/10seconds.run'] started"))
        self.assertEqual(0, popen.returncode)
        
    def test_normal_command_run_shutdown_from_outside(self):
        popen = self.run_docker('1', ['/etc/yasinit/10seconds.run', 'lorem'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        with self.assertRaises(subprocess.TimeoutExpired):
            (o, e) = popen.communicate(timeout = YasinitTest.OVERHEAD_FOR_DOCKER + 5)
            print("ERROR: This should not happen:\n{}\n{}\n".format(e, o))
        popen.terminate()
        (stdout_data, stderr_data) = popen.communicate(timeout = 2)
        self.assertEqual('lorem\n', stdout_data)
        self.assertIsNot(-1, stderr_data.find("Starting commands: [['/etc/yasinit/10seconds.run', 'lorem']]."))
        self.assertEqual(0, popen.returncode)
        

    def test_short_run_container(self):
        popen = self.run_docker('1', ['/bin/true'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        (stdout_data, stderr_data) = popen.communicate(timeout = YasinitTest.OVERHEAD_FOR_DOCKER + YasinitTest.SHUTDOWN_DURATION)
        self.assertEqual('', stdout_data)
        self.assertIsNot(-1, stderr_data.find("Command ['/bin/true'] started as pid "))
        self.assertEqual(0, popen.returncode)

    def test_short_run_failing_container(self):
        popen = self.run_docker('1', ['/bin/bash', '-c', 'exit 73'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        (stdout_data, stderr_data) = popen.communicate(timeout = YasinitTest.OVERHEAD_FOR_DOCKER + YasinitTest.SHUTDOWN_DURATION)
        self.assertEqual('', stdout_data)
        self.assertIsNot(-1, stderr_data.find("Command ['/bin/bash', '-c', 'exit 73'] started"))
        self.assertEqual(73, popen.returncode)
            
    def test_one_process_exits(self):
        popen = self.run_docker('2', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        (stdout_data, stderr_data) = popen.communicate(timeout = 6)

        self.assertEqual('', stdout_data)
        self.assertIsNot(-1, stderr_data.find("Command ['/etc/yasinit/10seconds.run'] started"))
        self.assertIsNot(-1, stderr_data.find("Command ['/etc/yasinit/2seconds_then_exit0.run'] started"))
        self.assertEqual(0, popen.returncode)

    def test_one_process_fails(self):
        popen = self.run_docker('3', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        (stdout_data, stderr_data) = popen.communicate(timeout = 2 + YasinitTest.OVERHEAD_FOR_DOCKER + YasinitTest.SHUTDOWN_DURATION)
        self.assertEqual('', stdout_data)
        self.assertIsNot(-1, stderr_data.find("Command ['/etc/yasinit/10seconds.run'] started"))
        self.assertIsNot(-1, stderr_data.find("Command ['/etc/yasinit/2seconds_then_fail.run'] started"))
        self.assertEqual(19, popen.returncode)

    def test_one_succeeds_quickly_other_barks_on_signal(self):
        popen = self.run_docker('4', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        (stdout_data, stderr_data) = popen.communicate(timeout = 2 + YasinitTest.OVERHEAD_FOR_DOCKER + YasinitTest.SHUTDOWN_DURATION)
        self.assertEqual('', stdout_data)
        self.assertIsNot(-1, stderr_data.find("Command ['/etc/yasinit/10seconds_fail_on_signal.run'] started"))
        self.assertIsNot(-1, stderr_data.find("Command ['/etc/yasinit/2seconds_then_exit0.run'] started"))
        self.assertEqual(23, popen.returncode)

    def test_one_succeeds_quickly_other_ignores_signal(self):
        popen = self.run_docker('5', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        with self.assertRaises(subprocess.TimeoutExpired):
            (out, err) = popen.communicate(timeout = 15 + YasinitTest.OVERHEAD_FOR_DOCKER + YasinitTest.SHUTDOWN_DURATION)
            print("ERROR: This was not supposed to happen:\n{}\n{}\n".format(out, err))
        (stdout_data, stderr_data) = popen.communicate(timeout = 7)
        self.assertEqual('', stdout_data)
        self.assertIsNot(-1, stderr_data.find("Command ['/etc/yasinit/ignore_signal.run'] started"))
        self.assertIsNot(-1, stderr_data.find("Command ['/etc/yasinit/2seconds_then_exit0.run'] started"))
        self.assertIsNot(-1, stderr_data.find("Shutdown failed, terminating even though some processes are still running. Pids: "))
        self.assertEqual(2, popen.returncode)

    def test_short_run_several_containers(self):
        popen = self.run_docker('6', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        (stdout_data, stderr_data) = popen.communicate(timeout=YasinitTest.OVERHEAD_FOR_DOCKER + YasinitTest.SHUTDOWN_DURATION)
        self.assertEqual('', stdout_data)
        self.assertIsNot(-1, stderr_data.find("Command ['/etc/yasinit/quick0.run'] started"))
        self.assertIsNot(-1, stderr_data.find("Command ['/etc/yasinit/quick1.run'] started"))
        self.assertIsNot(-1, stderr_data.find("Guarded process ['/etc/yasinit/quick0.run']"))
        self.assertIsNot(-1, stderr_data.find("Guarded process ['/etc/yasinit/quick1.run']"))
        self.assertEqual(0, popen.returncode)

    def test_short_run_several_containers_one_fails(self):
        popen = self.run_docker('7', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        (stdout_data, stderr_data) = popen.communicate(timeout=YasinitTest.OVERHEAD_FOR_DOCKER + YasinitTest.SHUTDOWN_DURATION)
        self.assertEqual('', stdout_data)
        self.assertIsNot(-1, stderr_data.find("Command ['/etc/yasinit/many_quick_0.run'] started"))
        self.assertIsNot(-1, stderr_data.find("Command ['/etc/yasinit/many_quick_1.run'] started"))
        self.assertIsNot(-1, stderr_data.find("Guarded process ['/etc/yasinit/many_quick_0.run']"))
        self.assertIsNot(-1, stderr_data.find("Guarded process ['/etc/yasinit/many_quick_1.run']"))
        self.assertEqual(1, popen.returncode)


