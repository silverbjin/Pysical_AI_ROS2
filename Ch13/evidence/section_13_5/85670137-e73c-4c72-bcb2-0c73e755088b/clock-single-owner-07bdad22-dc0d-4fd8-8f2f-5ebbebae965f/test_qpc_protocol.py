"""Owned real host replies, no engines, services or clock changes."""
import json,select,subprocess,time,unittest
from qpc_protocol import server_expression


class QpcProtocol(unittest.TestCase):
    def test_ready_follows_the_same_response_path_initialization(self):
        script=server_expression()
        self.assertLess(script.index('$null=Get-OriginalClockSample'),script.index('WriteLine("READY")'))
        self.assertEqual(script.count('ConvertTo-Json'),1)
        self.assertNotIn('$null=Get-OriginalClockSample',server_expression(warm=False))

    def test_real_host_reply_is_original_monotone_qpc_and_process_closes(self):
        path='/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
        p=subprocess.Popen([path,'-NoLogo','-NoProfile','-NonInteractive','-Command',server_expression()],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            self.assertTrue(select.select([p.stdout],[],[],5.)[0]);self.assertEqual(p.stdout.readline().strip(),'READY')
            rows=[]
            for _ in range(3):
                p.stdin.write('sample\n');p.stdin.flush()
                self.assertTrue(select.select([p.stdout],[],[],5.)[0]);rows.append(json.loads(p.stdout.readline()))
            self.assertTrue(all(r['frequency']>0 and r['qpc']>0 for r in rows))
            self.assertEqual(len({r['frequency'] for r in rows}),1)
            self.assertTrue(all(a['qpc']<b['qpc'] for a,b in zip(rows,rows[1:])))
        finally:
            p.stdin.write('stop\n');p.stdin.flush();p.stdin.close();p.wait(timeout=5.)
            stderr=p.stderr.read();p.stdout.close();p.stderr.close()
        self.assertEqual(p.returncode,0,stderr)


if __name__=='__main__':unittest.main()
