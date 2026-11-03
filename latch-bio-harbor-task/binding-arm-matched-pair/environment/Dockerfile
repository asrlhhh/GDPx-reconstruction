# Reconstructed environment for the "binding-arm matched pair" task.
# Provenance (from 12 agent rollouts; see ../RECONSTRUCTION.md):
#   * official full python:3.12.14 image on Debian bookworm (/usr/local/bin/python3.12 with only pip 25.0.1).
#     bookworm, not trixie: the original /root/.profile is 161 B dated 2019-07-09 (bookworm's stock file; trixie's is 132 B)
#   * Node.js v26.3.1 in /usr/local/bin (node binary 147,420,912 B, built 2026-06-17 17:39, as in the original listing),
#     npm/npx as absolute symlinks, no corepack/yarn
#   * analysis stack in a uv project venv /root/.venv built from /root/pyproject.toml + /root/uv.lock (not on PATH)
#   * task data /workspace/data/binding_panel_raw.xlsx (1,387,104 B in the original, mode 0644, mtime epoch 0)
FROM python:3.12.14-bookworm

# Node.js (the original image shipped node + absolute npm/npx symlinks in /usr/local/bin).
COPY --from=node:26.3.1-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:26.3.1-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -sf /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# Native libraries needed to build sdists that appear in the lock: pygeos -> GEOS; rpy2-rinterface (API mode,
# whose compiled _rinterface_cffi_api.abi3.so exists in the original venv) -> R headers/libR.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgeos-dev r-base-dev \
 && rm -rf /var/lib/apt/lists/*

# uv (not on PATH in the original image's /usr/local/bin; the usual /bin/uv copy pattern).
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /bin/

# Project venv. The original 925,103-byte uv.lock was not recoverable from the rollouts; it was resolved between
# 2026-06-08 and 2026-07-24 01:58 UTC. We re-resolve with --exclude-newer at the lock's mtime and constrain every
# package version that the rollouts printed (known-versions.txt, 85 pins incl. numpy 1.26.4 / pandas 2.3.3 /
# scipy 1.16.3 / openpyxl 3.1.5). The constraint table is added to a temporary copy of pyproject.toml only; the
# verbatim /root/pyproject.toml is restored afterwards.
WORKDIR /root
COPY pyproject.toml /root/pyproject.toml
COPY known-versions.txt /tmp/known-versions.txt
RUN cp /root/pyproject.toml /tmp/pyproject.verbatim.toml \
 && python3 -c "import pathlib; pins=[l.strip() for l in open('/tmp/known-versions.txt') if '==' in l]; p=pathlib.Path('/root/pyproject.toml'); p.write_text(p.read_text() + '\n[tool.uv]\nconstraint-dependencies = [\n' + ''.join('    \"%s\",\n' % x for x in pins) + ']\n')" \
 && UV_LINK_MODE=copy uv lock --exclude-newer 2026-07-24T01:58:00Z \
 && UV_LINK_MODE=copy uv sync --frozen --no-install-project \
 && cp /tmp/pyproject.verbatim.toml /root/pyproject.toml \
 && chmod 0664 /root/pyproject.toml /root/uv.lock \
 && rm -rf /root/.cache/uv /tmp/known-versions.txt /tmp/pyproject.verbatim.toml

# Import smoke test (also creates ~/.cache/<x> and ~/.config/<x>, as seen in the original /root listing).
RUN /root/.venv/bin/python -c "import numpy, pandas, scipy, openpyxl, matplotlib, h5py, anndata, scanpy; \
print(numpy.__version__, pandas.__version__, scipy.__version__, openpyxl.__version__)" \
 && rm -rf /root/.cache/uv

# Dotfiles: .bash_profile (42 B) sources .bashrc; the original 84-B .bashrc content was never printed and it did not
# activate the venv (every harness resolved `python` to /usr/local/bin/python).
COPY dotfiles/bash_profile /root/.bash_profile
COPY dotfiles/bashrc /root/.bashrc

# Task data (no other files in /workspace).
COPY data/binding_panel_raw.xlsx /workspace/data/binding_panel_raw.xlsx
RUN chmod 0644 /workspace/data/binding_panel_raw.xlsx && touch -d @0 /workspace/data/binding_panel_raw.xlsx

WORKDIR /workspace
