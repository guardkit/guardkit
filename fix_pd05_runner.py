if __name__ == '__main__':
    import sys
    sys.path.insert(0, '/Users/richardwoollcott/Projects/appmilla_github/guardkit')
    from pathlib import Path
    import os

    os.chdir('/Users/richardwoollcott/Projects/appmilla_github/guardkit')

    # Now run the inline fix
    exec(open('.claude/apply_fix_pd05_inline.py').read())
