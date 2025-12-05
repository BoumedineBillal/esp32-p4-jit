import os
import sys
import logging

# Add host directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'host')))

import p4jit
from p4jit.utils.logger import INFO_VERBOSE

def main():
    print("==============================================")
    print("       Simple P4JIT Logging Example           ")
    print("==============================================")
    print("This script demonstrates how to control the logging verbosity")
    print("of the P4JIT host toolchain.\n")

    # 1. Default Level (INFO)
    print("--- 1. Default Level (INFO) ---")
    print("Only high-level milestones are shown.")
    p4jit.set_log_level('INFO')
    
    # Create a dummy logger to simulate P4JIT internal logging
    # In a real scenario, these logs come from inside P4JIT classes
    logger = logging.getLogger('p4jit.test')
    
    logger.info("This is an INFO message (Visible)")
    logger.log(INFO_VERBOSE, "This is an INFO_VERBOSE message (Hidden)")
    logger.debug("This is a DEBUG message (Hidden)")
    print("")

    # 2. Detailed Level (INFO_VERBOSE)
    print("--- 2. Detailed Level (INFO_VERBOSE) ---")
    print("Shows operational steps like compilation and allocation.")
    p4jit.set_log_level('INFO_VERBOSE')
    
    logger.info("This is an INFO message (Visible)")
    logger.log(INFO_VERBOSE, "This is an INFO_VERBOSE message (Visible - Cyan)")
    logger.debug("This is a DEBUG message (Hidden)")
    print("")

    # 3. Debug Level (DEBUG)
    print("--- 3. Debug Level (DEBUG) ---")
    print("Shows everything, including internal data structures.")
    p4jit.set_log_level('DEBUG')
    
    logger.info("This is an INFO message (Visible)")
    logger.log(INFO_VERBOSE, "This is an INFO_VERBOSE message (Visible)")
    logger.debug("This is a DEBUG message (Visible - Grey)")
    print("")
    
    print("==============================================")
    print("Done! Use p4jit.set_log_level(level) to control this globally.")

if __name__ == "__main__":
    main()
