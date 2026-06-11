import unittest
import os
import shutil
import tempfile
from ides.mathex.kernel.session import KernelSession
from ides.mathex.kernel.executor import execute
from ides.mathex.kernel.path_manager import path_manager

class TestCWDIntegration(unittest.TestCase):
    """
    Integration Test:
    Verifies that the Kernel correctly identifies the Current Working Directory (CWD),
    finds .m files within it, and executes them as scripts (modifying globals).
    """

    def setUp(self):
        # 1. Create a temporary directory to act as our "Project Folder"
        self.test_dir = tempfile.mkdtemp()
        
        # 2. Save the original CWD so we can restore it later
        self.original_cwd = os.getcwd()
        
        # 3. Create a dummy .m script in this folder
        # Content: 'cwd_test_var = 42;'
        self.script_name = "test_cwd_script"
        self.file_path = os.path.join(self.test_dir, f"{self.script_name}.m")
        
        with open(self.file_path, "w") as f:
            f.write("cwd_test_var = 42;\n")
            f.write("disp('Script running from CWD...');\n")

        # 4. Switch the process CWD to this temp folder
        os.chdir(self.test_dir)
        
        # 5. Clear path_manager cache to ensure fresh lookup
        path_manager.clear_cache()
        
        # 6. Initialize Session
        self.session = KernelSession()

    def tearDown(self):
        # Restore CWD and clean up
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_run_script_by_name(self):
        """
        Scenario: User types 'test_cwd_script' in console.
        Expected: 
            - Loader finds test_cwd_script.m in CWD.
            - Executor runs it.
            - 'cwd_test_var' appears in workspace with value 42.
        """
        print(f"\n[Test] Running script '{self.script_name}' from {os.getcwd()}...")
        
        # Execute by name (implicit call)
        execute(self.script_name, self.session)
        
        # Check if the variable stuck
        self.assertIn("cwd_test_var", self.session.globals, "Variable from script failed to persist in Workspace.")
        self.assertEqual(self.session.globals["cwd_test_var"], 42, "Script execution did not produce correct value.")
        print("[Pass] Script executed and variables persisted.")

    def test_case_insensitive_lookup(self):
        """
        Scenario: User types 'TEST_CWD_SCRIPT' (wrong case).
        Expected: 
            - PathManager's case-insensitive fallback finds 'test_cwd_script.m'.
            - Script runs successfully.
        """
        wrong_case_name = self.script_name.upper() # "TEST_CWD_SCRIPT"
        print(f"\n[Test] Running case-mismatched script '{wrong_case_name}'...")
        
        # Execute
        execute(wrong_case_name, self.session)
        
        # Check persistence
        self.assertIn("cwd_test_var", self.session.globals, "Case-insensitive lookup failed.")
        print("[Pass] Case-insensitive lookup worked.")

if __name__ == "__main__":
    unittest.main()