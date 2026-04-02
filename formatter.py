import lldb
import sys
import os

# Make it so relative imports wor
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Now use absolute import
from array_ref import array_ref_summary, ArrayRefSyntheticChildProvider
from boolean_buffer import BooleanBufferSyntheticChildProvider
from scalar_buffer import scalar_buffer_array_summary, ScalarBufferSyntheticChildProvider

def primitive_array_summary(valueobj, internal_dict):
    return "test"

def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('script import __main__')
    
    import __main__
    __main__.ArrayRefSyntheticChildProvider = ArrayRefSyntheticChildProvider
    __main__.BooleanBufferSyntheticChildProvider = BooleanBufferSyntheticChildProvider
    __main__.ScalarBufferSyntheticChildProvider = ScalarBufferSyntheticChildProvider
    __main__.array_ref_summary = array_ref_summary
    __main__.arrow_array_summary = primitive_array_summary
    __main__.scalar_buffer_array_summary = scalar_buffer_array_summary
    
    
    import time
    time.sleep(0.1)

    debugger.HandleCommand(
        'type summary add -F __main__.array_ref_summary '
        '-x "^alloc::sync::Arc<dyn arrow_array::array::Array, .*$" '
        '-w arrow-rs'
    )
    debugger.HandleCommand(
        'type synthetic add '
        '-x "^alloc::sync::Arc<dyn arrow_array::array::Array, .*$" '
        '-w arrow-rs '
        '-l __main__.ArrayRefSyntheticChildProvider'
    )

    debugger.HandleCommand(
        'type synthetic add '
        '-x "^arrow_buffer::buffer::boolean::BooleanBuffer$" '
        '-w arrow-rs '
        '-l __main__.BooleanBufferSyntheticChildProvider'
    )

    # debugger.HandleCommand(
    #     'type summary add -F __main__.primitive_array_summary '
    #     '-x "^arrow_array::array::primitive_array::PrimitiveArray<.*>$" '
    #     '-w arrow-rs'
    # )

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