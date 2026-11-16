# Validating the RO-Crate in a bundle

Every finished FDOx bundle (`<name>-fdo-bundle.zip`) is also an
[RO-Crate 1.2](https://w3id.org/ro/crate/1.2): `ro-crate-metadata.json` sits at
its root. This page shows, step by step, how to check that with the
community validator [`roc-validator`](https://github.com/crs4/rocrate-validator).
It takes about five minutes and needs no knowledge of FDOx.

## What you need

- Python 3.9 or newer and `pip`.
- A bundle: either one you built (`output/<name>-fdo-bundle.zip`, or
  `dist/<slug>_release/<slug>-fdo-bundle.zip` from
  [fdo-3d-packager](https://github.com/FDOx-squirrel/fdo-3d-packager)) or one
  you downloaded, for example from Zenodo.
- Internet access while the validator runs: some of its checks read the
  RO-Crate context and related resources from the web.

## Step 1: install the validator

A virtual environment keeps it separate from your other Python packages
(optional, but tidy).

Windows (cmd):

```cmd
python -m venv rocv && rocv\Scripts\activate && pip install roc-validator && rocrate-validator --version
```

Linux / macOS:

```bash
python3 -m venv rocv && source rocv/bin/activate && pip install roc-validator && rocrate-validator --version
```

The last command prints the validator's version. This page was written
against 0.13.1.

## Step 2: unpack the bundle into an empty folder

The validator reads a crate from a folder. A bundle is an ordinary ZIP, so
unpack it. Use a new, empty folder so nothing else ends up in the crate.

Windows (cmd), replacing `Q60-fdo-bundle.zip` with your bundle:

```cmd
mkdir crate && tar -xf Q60-fdo-bundle.zip -C crate
```

Linux / macOS:

```bash
mkdir crate && unzip -q Q60-fdo-bundle.zip -d crate
```

Check that `crate/ro-crate-metadata.json` exists. If it does not, the bundle was
built before fdo-squirrel v1.1.0, which introduced the RO-Crate export.

## Step 3: run the validation

```bash
rocrate-validator validate crate
```

(the same command on Windows). It takes a few seconds, then prints a report.

## Step 4: read the result

The last line of the report is the verdict. For a bundle built with
fdo-squirrel v1.1.0 or newer it reads:

```
RO-Crate is a valid ro-crate-1.2 !!!
```

Above it the report counts the checks. A valid Q60 bundle gave 63 passed,
0 failed and 3 skipped (validator 0.13.1, profile `ro-crate-1.2`, severity
`REQUIRED`, 16 November 2026). Your numbers can differ with another
validator version or another package; what matters is **0 failed**.

- **passed**: the crate meets the requirement.
- **failed**: it does not. The report names the requirement and the entity in
  `ro-crate-metadata.json` that triggered it.
- **skipped**: the validator did not evaluate the check for this crate.

### The warning at the end

You will most likely see this under the report:

```
WARNING in profile_detection: The conformance to the following profiles could not be
verified: https://w3id.org/fdo-squirrel/profile/ro-crate/1.0
```

It is expected and does not make the crate invalid. The crate declares that it
also follows the FDOx profile (see [the profile description](ro-crate-profile.md)),
and the validator cannot look that profile up, because the persistent
identifier is not registered yet. The check against RO-Crate 1.2 itself is
unaffected.

## If something goes wrong

| What you see | Likely cause and fix |
|---|---|
| `rocrate-validator` is not found | The virtual environment is not active (run the `activate` line again), or the install failed (re-run `pip install roc-validator`). |
| `URLError`, `Tunnel connection failed` or a `403` during a check | No internet access, or a proxy or firewall blocks the request. Run it from a network that can reach the web. |
| `ro-crate-metadata.json` not found | You validated the ZIP's parent folder or an empty folder. Point the command at the folder that directly contains `ro-crate-metadata.json`. |
| Checks `failed` | Open an issue at [fdo-squirrel](https://github.com/FDOx-squirrel/fdo-squirrel/issues) and attach the report. Please state the fdo-squirrel version (it is in `FDOx.yaml` in the bundle). |

## Optional: also check the Signposting side

The bundle also contains a landing page with FAIR Signposting links. The
checker
[`tools/check_signposting.py`](https://github.com/FDOx-squirrel/fdo-squirrel/blob/main/tools/check_signposting.py)
reports those links for a published record or for a local landing page; see
[Signposting](signposting.md) for how to use it.
