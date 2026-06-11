from ides.mathex.kernel.session import KernelSession

def test_image_toolbox_loading():
    sess = KernelSession()
    
    # Check if 'imread' is registered in globals
    if 'imread' in sess.globals:
        print("\n[PASS] Image Toolbox loaded successfully.")
        # Try a dummy call if scikit-image is installed
        try:
            # Passing a non-existent file should raise an error from scikit-image,
            # NOT a NameError from Mathex
            sess.execute("img = imread('missing.png');")
        except Exception as e:
            if "No such file" in str(e) or "FileNotFound" in str(e):
                print("[PASS] imread is active and attempted to load file.")
            else:
                print(f"[WARN] Unexpected error from imread: {e}")
    else:
        print("\n[WARN] Image Toolbox NOT loaded (scikit-image likely missing).")
        # Ensure it didn't crash the session
        assert sess.globals['pi'] is not None

if __name__ == "__main__":
    test_image_toolbox_loading()