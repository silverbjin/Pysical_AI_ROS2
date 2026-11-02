"""Plans use only approved per-engine profiles, before any service or engine."""
import importlib.util,json,subprocess,sys,unittest
from pathlib import Path

TASK=Path(__file__).resolve().parent
def api():
    path=TASK/'native_engine_plan.py'
    if not path.exists():raise AssertionError('reviewable per-engine validation plan missing')
    spec=importlib.util.spec_from_file_location('native_engine_plan',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class NativeEnginePlanTests(unittest.TestCase):
    def plan(self,engine,clock='relay100'):
        return api().g1_plan(engine,Path('/owned/output'),Path('/owned/prepared'),
            Path('/owned/prepared/scene'),Path('/owned/prepared/carry_profile.json'),clock,'native_cdr')

    def test_mujoco_never_inherits_declined_interpolation_or_dart(self):
        value=self.plan('mujoco')
        self.assertEqual(value['position_reference_mode'],'native')
        self.assertEqual(value['dart_contact_mode'],'native')
        self.assertNotIn('--g1-reference-ramp',value['prepare_command'])
        self.assertNotIn('--g1-contact-allowance',value['prepare_command'])
        command=value['command'];self.assertEqual(command[command.index('--engine')+1],'mujoco')

    def test_gazebo_plan_selects_the_exact_approved_profile(self):
        value=self.plan('gazebo')
        self.assertEqual(value['position_reference_mode'],'g1_ramp20ms')
        self.assertEqual(value['dart_contact_mode'],'allowance50um')
        self.assertIn('--g1-reference-ramp',value['prepare_command'])
        self.assertIn('--g1-contact-allowance',value['prepare_command'])
        command=value['command'];self.assertEqual(command[command.index('--dart-contact-mode')+1],'allowance50um')
        self.assertEqual(command[command.index('--observer-backend')+1],'native_cdr')

    def test_unknown_engine_and_unscoped_gazebo_are_rejected(self):
        with self.assertRaises(ValueError):self.plan('other')
        with self.assertRaises(ValueError):self.plan('gazebo','native')

    def test_root_validation_command_is_a_fixed_script_and_engine(self):
        module=api();root=Path('/owned/session')
        command=module.validation_command('gazebo',root,3)
        self.assertEqual(command,['bash',str(root/'timesync-comparison-user.sh'),str(root),'','3','gazebo'])
        self.assertEqual(module.validation_command('mujoco',root,1)[-1],'mujoco')
        for engine,pairs in (('bad',3),('gazebo',2)):
            with self.assertRaises(ValueError):module.validation_command(engine,root,pairs)

    def test_actual_driver_dry_run_starts_no_process_or_evidence_directory(self):
        script=TASK/'native-output-g1.py'
        self.assertTrue(script.exists(),'generic G1 validation driver missing')
        result=subprocess.run([sys.executable,str(script),'--engine','gazebo',
            '--control-clock-mode','relay100','--observer-backend','native_cdr','--plan-only'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        value=json.loads(result.stdout)
        self.assertFalse(value['executed'])
        self.assertEqual(value['child_processes_started'],0)
        self.assertEqual(value['engine'],'gazebo')
        self.assertIn('--g1-reference-ramp',value['prepare_command'])

    def test_invalid_root_engine_is_rejected_before_platform_or_service_operations(self):
        result=subprocess.run([sys.executable,str(TASK/'temporary-clock-session.py'),
            '--engine','invalid','--service-only'],capture_output=True,text=True)
        self.assertEqual(result.returncode,2,result.stderr)
        self.assertIn('invalid choice',result.stderr)

if __name__=='__main__':unittest.main()
