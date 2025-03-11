import logging
import traceback

# Create a debug logger
debug_logger = logging.getLogger('debug')
debug_logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('log_source_debug.log')
debug_logger.addHandler(file_handler)

# Store the original _log method
original_log = logging.Logger._log

# Define a replacement that traces binary logs
def _trace_log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
    if isinstance(msg, (bytes, bytearray)) or (isinstance(msg, str) and len(msg) > 1000 and 
                                             sum(c.isprintable() for c in msg[:100]) < 80):
        # Log where binary data is coming from
        stack = traceback.extract_stack()
        debug_logger.debug(f"Binary data logging detected from: {stack[-3]}")
        # Skip the binary log
        return
        
    # Call the original method for non-binary data
    original_log(self, level, msg, args, exc_info, extra, stack_info, stacklevel)

# Replace the _log method with our tracing version
logging.Logger._log = _trace_log 