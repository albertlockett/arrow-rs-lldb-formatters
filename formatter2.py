import lldb
import sys
import os

# Make it so relative imports wor
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Now use absolute import
from scalar_buffer import scalar_buffer_array_summary, ScalarBufferSyntheticChildProvider

def primitive_array_summary(valueobj, internal_dict):
    return "test"

def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('script import __main__')
    
    import __main__
    __main__.arrow_array_summary = primitive_array_summary
    __main__.scalar_buffer_array_summary = scalar_buffer_array_summary
    __main__.ScalarBufferSyntheticChildProvider = ScalarBufferSyntheticChildProvider
    
    import time
    time.sleep(0.1)

    # Array formatters (summaries)
    debugger.HandleCommand(
        'type summary add -F __main__.arrow_array_summary '
        '-x "^arrow_array::array::primitive_array::PrimitiveArray<.*>$" '
        '-w arrow-rs'
    )

    debugger.HandleCommand(
        'type summary add -F __main__.scalar_buffer_array_summary '
        '-x "^arrow_buffer::buffer::scalar::ScalarBuffer<.*>$" '
        '-w arrow-rs'
    )

    debugger.HandleCommand(
        'type synthetic add '
        '-x "^arrow_buffer::buffer::scalar::ScalarBuffer<.*>$" '
        '-w arrow-rs '
        '-l __main__.ScalarBufferSyntheticChildProvider'
    )

    debugger.HandleCommand('type category enable arrow-rs')
    print("Arrow-rs formatters loaded")