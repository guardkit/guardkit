richardwoollcott@Mac FEAT-FHE % python3 -m venv .venv
richardwoollcott@Mac FEAT-FHE % source .venv/bin/activate
(.venv) richardwoollcott@Mac FEAT-FHE % pip install -e ".[dev]"

Obtaining file:///Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-FHE
  Installing build dependencies ... done
  Checking if build backend supports build_editable ... done
  Getting requirements to build editable ... done
  Preparing editable metadata (pyproject.toml) ... done
Collecting fastapi>=0.104.0 (from feature-test==0.1.0)
  Using cached fastapi-0.128.0-py3-none-any.whl.metadata (30 kB)
Collecting uvicorn>=0.24.0 (from uvicorn[standard]>=0.24.0->feature-test==0.1.0)
  Using cached uvicorn-0.40.0-py3-none-any.whl.metadata (6.7 kB)
Collecting pydantic>=2.0.0 (from feature-test==0.1.0)
  Using cached pydantic-2.12.5-py3-none-any.whl.metadata (90 kB)
Collecting pytest>=7.4.0 (from feature-test==0.1.0)
  Using cached pytest-9.0.2-py3-none-any.whl.metadata (7.6 kB)
Collecting pytest-asyncio>=0.21.0 (from feature-test==0.1.0)
  Using cached pytest_asyncio-1.3.0-py3-none-any.whl.metadata (4.1 kB)
Collecting httpx>=0.25.0 (from feature-test==0.1.0)
  Using cached httpx-0.28.1-py3-none-any.whl.metadata (7.1 kB)
Collecting pytest-cov (from feature-test==0.1.0)
  Using cached pytest_cov-7.0.0-py3-none-any.whl.metadata (31 kB)
Collecting ruff (from feature-test==0.1.0)
  Using cached ruff-0.14.14-py3-none-macosx_11_0_arm64.whl.metadata (26 kB)
Collecting starlette<0.51.0,>=0.40.0 (from fastapi>=0.104.0->feature-test==0.1.0)
  Using cached starlette-0.50.0-py3-none-any.whl.metadata (6.3 kB)
Collecting typing-extensions>=4.8.0 (from fastapi>=0.104.0->feature-test==0.1.0)
  Using cached typing_extensions-4.15.0-py3-none-any.whl.metadata (3.3 kB)
Collecting annotated-doc>=0.0.2 (from fastapi>=0.104.0->feature-test==0.1.0)
  Using cached annotated_doc-0.0.4-py3-none-any.whl.metadata (6.6 kB)
Collecting anyio<5,>=3.6.2 (from starlette<0.51.0,>=0.40.0->fastapi>=0.104.0->feature-test==0.1.0)
  Using cached anyio-4.12.1-py3-none-any.whl.metadata (4.3 kB)
Collecting idna>=2.8 (from anyio<5,>=3.6.2->starlette<0.51.0,>=0.40.0->fastapi>=0.104.0->feature-test==0.1.0)
  Using cached idna-3.11-py3-none-any.whl.metadata (8.4 kB)
Collecting certifi (from httpx>=0.25.0->feature-test==0.1.0)
  Using cached certifi-2026.1.4-py3-none-any.whl.metadata (2.5 kB)
Collecting httpcore==1.* (from httpx>=0.25.0->feature-test==0.1.0)
  Using cached httpcore-1.0.9-py3-none-any.whl.metadata (21 kB)
Collecting h11>=0.16 (from httpcore==1.*->httpx>=0.25.0->feature-test==0.1.0)
  Using cached h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
Collecting annotated-types>=0.6.0 (from pydantic>=2.0.0->feature-test==0.1.0)
  Using cached annotated_types-0.7.0-py3-none-any.whl.metadata (15 kB)
Collecting pydantic-core==2.41.5 (from pydantic>=2.0.0->feature-test==0.1.0)
  Using cached pydantic_core-2.41.5-cp314-cp314-macosx_11_0_arm64.whl.metadata (7.3 kB)
Collecting typing-inspection>=0.4.2 (from pydantic>=2.0.0->feature-test==0.1.0)
  Using cached typing_inspection-0.4.2-py3-none-any.whl.metadata (2.6 kB)
Collecting iniconfig>=1.0.1 (from pytest>=7.4.0->feature-test==0.1.0)
  Using cached iniconfig-2.3.0-py3-none-any.whl.metadata (2.5 kB)
Collecting packaging>=22 (from pytest>=7.4.0->feature-test==0.1.0)
  Using cached packaging-26.0-py3-none-any.whl.metadata (3.3 kB)
Collecting pluggy<2,>=1.5 (from pytest>=7.4.0->feature-test==0.1.0)
  Using cached pluggy-1.6.0-py3-none-any.whl.metadata (4.8 kB)
Collecting pygments>=2.7.2 (from pytest>=7.4.0->feature-test==0.1.0)
  Using cached pygments-2.19.2-py3-none-any.whl.metadata (2.5 kB)
Collecting click>=7.0 (from uvicorn>=0.24.0->uvicorn[standard]>=0.24.0->feature-test==0.1.0)
  Using cached click-8.3.1-py3-none-any.whl.metadata (2.6 kB)
Collecting httptools>=0.6.3 (from uvicorn[standard]>=0.24.0->feature-test==0.1.0)
  Using cached httptools-0.7.1-cp314-cp314-macosx_11_0_arm64.whl.metadata (3.5 kB)
Collecting python-dotenv>=0.13 (from uvicorn[standard]>=0.24.0->feature-test==0.1.0)
  Using cached python_dotenv-1.2.1-py3-none-any.whl.metadata (25 kB)
Collecting pyyaml>=5.1 (from uvicorn[standard]>=0.24.0->feature-test==0.1.0)
  Using cached pyyaml-6.0.3-cp314-cp314-macosx_11_0_arm64.whl.metadata (2.4 kB)
Collecting uvloop>=0.15.1 (from uvicorn[standard]>=0.24.0->feature-test==0.1.0)
  Using cached uvloop-0.22.1-cp314-cp314-macosx_10_13_universal2.whl.metadata (4.9 kB)
Collecting watchfiles>=0.13 (from uvicorn[standard]>=0.24.0->feature-test==0.1.0)
  Using cached watchfiles-1.1.1-cp314-cp314-macosx_11_0_arm64.whl.metadata (4.9 kB)
Collecting websockets>=10.4 (from uvicorn[standard]>=0.24.0->feature-test==0.1.0)
  Using cached websockets-16.0-cp314-cp314-macosx_11_0_arm64.whl.metadata (6.8 kB)
Collecting coverage>=7.10.6 (from coverage[toml]>=7.10.6->pytest-cov->feature-test==0.1.0)
  Using cached coverage-7.13.1-cp314-cp314-macosx_11_0_arm64.whl.metadata (8.5 kB)
Using cached fastapi-0.128.0-py3-none-any.whl (103 kB)
Using cached starlette-0.50.0-py3-none-any.whl (74 kB)
Using cached anyio-4.12.1-py3-none-any.whl (113 kB)
Using cached annotated_doc-0.0.4-py3-none-any.whl (5.3 kB)
Using cached httpx-0.28.1-py3-none-any.whl (73 kB)
Using cached httpcore-1.0.9-py3-none-any.whl (78 kB)
Using cached h11-0.16.0-py3-none-any.whl (37 kB)
Using cached idna-3.11-py3-none-any.whl (71 kB)
Using cached pydantic-2.12.5-py3-none-any.whl (463 kB)
Using cached pydantic_core-2.41.5-cp314-cp314-macosx_11_0_arm64.whl (1.9 MB)
Using cached annotated_types-0.7.0-py3-none-any.whl (13 kB)
Using cached pytest-9.0.2-py3-none-any.whl (374 kB)
Using cached pluggy-1.6.0-py3-none-any.whl (20 kB)
Using cached iniconfig-2.3.0-py3-none-any.whl (7.5 kB)
Using cached packaging-26.0-py3-none-any.whl (74 kB)
Using cached pygments-2.19.2-py3-none-any.whl (1.2 MB)
Using cached pytest_asyncio-1.3.0-py3-none-any.whl (15 kB)
Using cached typing_extensions-4.15.0-py3-none-any.whl (44 kB)
Using cached typing_inspection-0.4.2-py3-none-any.whl (14 kB)
Using cached uvicorn-0.40.0-py3-none-any.whl (68 kB)
Using cached click-8.3.1-py3-none-any.whl (108 kB)
Using cached httptools-0.7.1-cp314-cp314-macosx_11_0_arm64.whl (108 kB)
Using cached python_dotenv-1.2.1-py3-none-any.whl (21 kB)
Using cached pyyaml-6.0.3-cp314-cp314-macosx_11_0_arm64.whl (173 kB)
Using cached uvloop-0.22.1-cp314-cp314-macosx_10_13_universal2.whl (1.4 MB)
Using cached watchfiles-1.1.1-cp314-cp314-macosx_11_0_arm64.whl (390 kB)
Using cached websockets-16.0-cp314-cp314-macosx_11_0_arm64.whl (175 kB)
Using cached certifi-2026.1.4-py3-none-any.whl (152 kB)
Using cached pytest_cov-7.0.0-py3-none-any.whl (22 kB)
Using cached coverage-7.13.1-cp314-cp314-macosx_11_0_arm64.whl (219 kB)
Using cached ruff-0.14.14-py3-none-macosx_11_0_arm64.whl (10.2 MB)
Building wheels for collected packages: feature-test
  Building editable for feature-test (pyproject.toml) ... done
  Created wheel for feature-test: filename=feature_test-0.1.0-0.editable-py3-none-any.whl size=1545 sha256=6e5cd4fde5202962e4edb828b22822aa6d5efd07668df79fa0ef5f4a03b14134
  Stored in directory: /private/var/folders/75/prgjl4_x0k3_6tj58k39db1r0000gn/T/pip-ephem-wheel-cache-zvbdgsy2/wheels/70/10/6c/398b42cf1cc62ab79d9d823676614bc8bcf7a07d410f5f3562
Successfully built feature-test
Installing collected packages: websockets, uvloop, typing-extensions, ruff, pyyaml, python-dotenv, pygments, pluggy, packaging, iniconfig, idna, httptools, h11, coverage, click, certifi, annotated-types, annotated-doc, uvicorn, typing-inspection, pytest, pydantic-core, httpcore, anyio, watchfiles, starlette, pytest-cov, pytest-asyncio, pydantic, httpx, fastapi, feature-test
Successfully installed annotated-doc-0.0.4 annotated-types-0.7.0 anyio-4.12.1 certifi-2026.1.4 click-8.3.1 coverage-7.13.1 fastapi-0.128.0 feature-test-0.1.0 h11-0.16.0 httpcore-1.0.9 httptools-0.7.1 httpx-0.28.1 idna-3.11 iniconfig-2.3.0 packaging-26.0 pluggy-1.6.0 pydantic-2.12.5 pydantic-core-2.41.5 pygments-2.19.2 pytest-9.0.2 pytest-asyncio-1.3.0 pytest-cov-7.0.0 python-dotenv-1.2.1 pyyaml-6.0.3 ruff-0.14.14 starlette-0.50.0 typing-extensions-4.15.0 typing-inspection-0.4.2 uvicorn-0.40.0 uvloop-0.22.1 watchfiles-1.1.1 websockets-16.0
(.venv) richardwoollcott@Mac FEAT-FHE %
(.venv) richardwoollcott@Mac FEAT-FHE %
(.venv) richardwoollcott@Mac FEAT-FHE %
(.venv) richardwoollcott@Mac FEAT-FHE %
(.venv) richardwoollcott@Mac FEAT-FHE %
(.venv) richardwoollcott@Mac FEAT-FHE % uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

Traceback (most recent call last):
  File "/opt/homebrew/bin/uvicorn", line 5, in <module>
    from uvicorn.main import main
ModuleNotFoundError: No module named 'uvicorn'
(.venv) richardwoollcott@Mac FEAT-FHE %