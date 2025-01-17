try:
    import platform
    import subprocess
    import logging
    from importlib_metadata import distributions
    import torch
    import os  # Import the os module
    import re
    import glob
    import textwrap
    import packaging.version
    import packaging.specifiers
    from packaging.specifiers import SpecifierSet
    from packaging.specifiers import SpecifierSet
    from packaging.version import parse as parse_version
except ImportError as e:
    print(f"\033[91mError importing module: {e}\033[0m\n")
    print("\033[94mPlease ensure you started the Text-generation-webUI Python environment with either\033[0m")
    print("\033[92mcmd_linux.sh\033[0m, \033[92mcmd_windows.bat\033[0m, \033[92mcmd_macos.sh\033[0m, or \033[92mcmd_wsl.bat\033[0m")
    print("\033[94mand then try running the diagnostics again.\033[0m")
    exit(1)

try:
    import psutil
except ImportError:
    print("psutil not found. Installing...")
    subprocess.run(['pip', 'install', 'psutil'])
    import psutil

def get_requirements_file():
    requirements_files = glob.glob("requirements*.txt")
    if not requirements_files:
        print("\033[91mNo requirements files found.\033[0m")
        return None

    print("\033[94m\nSelect a requirements file to check against (or press Enter for default 'requirements.txt'):\033[0m\n")
    for i, file in enumerate(requirements_files, start=1):
        print(f"{i}. {file}")

    choice = input("\nEnter the number of your choice: ")
    try:
        choice = int(choice) - 1
        return requirements_files[choice]
    except (ValueError, IndexError):
        return "requirements.txt"

# Set up logging with filemode='w'
logging.basicConfig(filename='diagnostics.log', filemode='w', level=logging.INFO)

# Function to get GPU information using subprocess
def get_gpu_info():
    try:
        result = subprocess.run(['nvidia-smi'], stdout=subprocess.PIPE, text=True)
        return result.stdout
    except FileNotFoundError:
        return "NVIDIA GPU information not available"

# Function to check if a port is in use
def is_port_in_use(port):
    for conn in psutil.net_connections():
        if conn.laddr.port == port:
            return True
    return False

def satisfies_wildcard(installed_version, required_version):
    if '*' in required_version:
        required_parts = required_version.split('.')
        installed_parts = installed_version.split('.')
        for req, inst in zip(required_parts, installed_parts):
            if req != '*' and req != inst:
                return False
        return True
    return False

# Function to log and print system information
def log_system_info():
    # System information
    os_version = platform.system() + " " + platform.version()
    
    # Get CUDA_HOME environment variable
    cuda_home = os.environ.get('CUDA_HOME', 'N/A')

    gpu_info = get_gpu_info()

    # Python environment information
    python_version = platform.python_version()

    # Torch version
    torch_version = torch.__version__

    # System RAM using psutil
    try:
        virtual_memory = psutil.virtual_memory()
        total_ram = f"{virtual_memory.total / (1024 ** 3):.2f} GB"
        available_ram = f"{virtual_memory.available / (1024 ** 3):.2f} GB"
        system_ram = f"{available_ram} available out of {total_ram} total"
    except NameError:
        print("psutil is not installed. Unable to check system RAM.")
        system_ram = "N/A"

    # Port check (if psutil is available)
    port_status = "N/A"
    if 'psutil' in globals():
        port_to_check = 7851
        if is_port_in_use(port_to_check):
            port_status = f"Port {port_to_check} is in use."
        else:
            port_status = f"Port {port_to_check} is available."

    # Package versions using importlib_metadata
    package_versions = {d.metadata['Name']: d.version for d in distributions()}

    # Compare with requirements file
    requirements_file = get_requirements_file()
    if requirements_file:
        required_packages = {}
        installed_packages = {}

        try:
            with open(requirements_file, 'r') as req_file:
                requirements = [line.strip() for line in req_file]
                for req in requirements:
                    # Use regular expression to parse package name and version
                    match = re.match(r'([^\s>=]+)\s*([>=<]+)\s*([^,]+)', req)
                    if match:
                        package_name, operator, version_spec = match.groups()
                        installed_version = package_versions.get(package_name, 'Not installed')
                        if installed_version != 'Not installed':
                            required_packages[package_name] = (operator, version_spec)
                            installed_packages[package_name] = installed_version
        except FileNotFoundError:
            print(f"\n{requirements_file} not found. Skipping version checks.")
            logging.info(f"NOTE {requirements_file} not found. Skipping version checks.")

    # Log and print information
    logging.info(f"OS Version: {os_version}")
    logging.info(f"Note: Windows 11 build is 10.x.22xxx")
    logging.info(f"Python Version: {python_version}")
    logging.info(f"Torch Version: {torch_version}")
    logging.info(f"System RAM: {system_ram}")
    logging.info(f"CUDA_HOME: {cuda_home}")
    logging.info(f"Port Status: {port_status}")
    if required_packages:  # Check if the dictionary is not empty
        logging.info("Package Versions:")
        max_package_length = max(len(package) for package in required_packages.keys())
        for package_name, (operator, required_version) in required_packages.items():
            installed_version = installed_packages.get(package_name, 'Not installed')
            logging.info(f"{package_name.ljust(max_package_length)}  Required: {operator} {required_version.ljust(12)}  Installed: {installed_version}")
    logging.info(f"GPU Information:\n{gpu_info}")
    logging.info("Package Versions:")
    for package, version in package_versions.items():
        logging.info(f"{package}>= {version}")

    # Print to screen
    print(f"\n\033[94mOS Version:\033[0m \033[92m{os_version}\033[0m")
    print(f"\033[94mOS Ver note:\033[0m \033[92mWindows 11 build is 10.x.22xxx\033[0m")
    print(f"\033[94mCUDA_HOME:\033[0m \033[92m{cuda_home}\033[0m")
    print(f"\033[94mSystem RAM:\033[0m \033[92m{system_ram}\033[0m")
    print(f"\033[94mPort Status:\033[0m \033[92m{port_status}\033[0m")
    print(f"\033[94mTorch Version:\033[0m \033[92m{torch_version}\033[0m")
    print(f"\033[94mPython Version:\033[0m \033[92m{python_version}\033[0m")
    if required_packages:  # Check if the dictionary is not empty
        print("\033[94m\nRequirements file package comparison:\033[0m")
        max_package_length = max(len(package) for package in required_packages.keys())

        for package_name, (operator, required_version) in required_packages.items():
            installed_version = installed_packages.get(package_name, 'Not installed')

            # Exclude build information (e.g., +cu118) before creating the SpecifierSet
            required_version_no_build = required_version.split("+")[0]

            if '*' in required_version:
                condition_met = satisfies_wildcard(installed_version, required_version)
            else:
                # Compare versions using packaging.version
                required_specifier = SpecifierSet(f"{operator}{required_version_no_build}")
                installed_version = parse_version(installed_version)
                condition_met = installed_version in required_specifier

            color_required = "\033[92m" if condition_met else "\033[91m"
            color_installed = "\033[92m" if condition_met else "\033[91m"

            # Print colored output
            print(f"{package_name.ljust(max_package_length)}  Required: {color_required}{operator} {required_version.ljust(12)}\033[0m  Installed: {color_installed}{installed_version}\033[0m")
        print("\033[94m\nRequirements file specifier meanings:\033[0m")
        explanation = textwrap.dedent("""
        == Exact version              != Any version except          < Less than               
        <= Less than or equal to      >  Greater than                >= Greater than or equal to
        ~ Compatible release          ;  Environment marker          AND Logical AND           
        OR Logical OR
        """)
        print(explanation.strip())
    print("")
    print(f"GPU Information:{gpu_info}")
    print(f"\033[94mDiagnostic log created:\033[0m \033[92mdiagnostics.log\033[0m")
    print(f"\033[94mPlease upload the log file with any support ticket.\033[0m")

if __name__ == "__main__":
    log_system_info()