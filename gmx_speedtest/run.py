import sys
import os
import subprocess
import multiprocessing
RUNTIME = os.environ.get("RUNTIME")
if RUNTIME is None:
    RUNTIME = 0.002 # hours
else:
    RUNTIME = float(RUNTIME)


def check_gmx(env):
    """ Check that gmx is installed, report version and executable. """
    proc = subprocess.run("gmx --version", shell=True, check=True, capture_output=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError("Error: gmx --version failed")
    out = proc.stdout.decode("utf-8").split("\n")
    for line in out:
        if "GROMACS version:" in line:
            version = line.split(":")[1].strip()
        if "GPU support:" in line:
            gpu = line.split(":")[1].strip()
        if "Executable:" in line:
            exe = line.split(":")[1].strip()
    print(f"Found gmx version:\n\t{version}")
    print(f"GPU support:\n\t{gpu}")
    print(f"Found gmx installation:\n\t{exe}")


def get_env():
    """ Get environment variables relevant to GROMACS. """
    keys_to_copy = ["PATH", "GMXBIN", "GMXLDLIB", "GMXMAN", "GMXDATA"]
    env = {}
    for key, value in os.environ.items():
        if key in keys_to_copy:
            env[key] = value
    return env

def run_single(tpr_file, plumed_file, extra_args, n_cores):
    """ Run a single test with n_cores cores. """
    command = f"gmx mdrun -deffnm {tpr_file[:-4]}"
    if plumed_file is not None:
        command += f" -plumed {plumed_file}"
    if extra_args is not None:
        command += " {}".format(" ".join(extra_args))
    command += f" -s {tpr_file}"
    command += f" -nt {n_cores}"
    command += " -nsteps -1"
    command += f" -maxh {RUNTIME}"
    command += " --pin on"
    print(f"{command=}", end="\r")
    try:
        proc = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True
        )
        output = proc.stderr.decode("utf-8").split("\n")
        # clear shell
        print(80 * " ", end="\r")
        for line in output:
            # print(f"{line=}")
            if "Performance:" in line:
                print(f"nt: {n_cores}            (ns/day)    (hour/ns)")
                print(f"{line}\n")
                return False, command
        # print(out.split("\n"))
    except Exception:
        print("Command failed")
        return True, command


def make_error_message(err_cmd):
    subprocess.run(err_cmd, shell=True, check=True)


def run_speedtest():
    """ Test how the speed of gmx simulation compares using diff n of threads. """
    print("Welcome to gmx_speedtest! \n")
    # check tpr file input
    tpr_file = sys.argv[1]
    if not tpr_file.endswith(".tpr"):
        raise ValueError("Error: tpr file must end with .tpr")
    print(f"Using tpr file:\n\t{tpr_file}")
    # check plumed file input
    if len(sys.argv) > 2:
        plumed_file = sys.argv[2]
        if not plumed_file or plumed_file == "false":
            plumed_file = None
        else:
            print(f"Using plumed file:\n\t{plumed_file}")
    else:
        plumed_file = None
    # check extra arguments
    extra_args = None
    if len(sys.argv) > 3:
        extra_args  = sys.argv[3:]
        print(f"Using extra args:\n\t{extra_args}")

    # test gmx installation
    env = get_env()
    check_gmx(env)
    print("To change the length of the test runs, set env variable $RUNTIME (hours).\n")

    # run speedtest
    for i in range(1, multiprocessing.cpu_count()):
        print(f"Running speedtest with {i} cores...", end="\r")
        err, cmd = run_single(tpr_file, plumed_file, extra_args, i)
        if err:
            make_error_message(cmd)


if __name__ == "__main__":
    run_speedtest()

