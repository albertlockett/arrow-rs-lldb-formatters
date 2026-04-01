import lldb

def arrow_array_summary(valobj, internal_dict):
    type_name = valobj.GetTypeName()
    
    try:
        # For Arc<dyn Array>, get some useful info
        if type_name.startswith("alloc::sync::Arc"):
            # You can drill into the structure here
            ptr = valobj.GetChildMemberWithName("ptr")
            if ptr.IsValid():
                return f"Arc<dyn Array>"
            return "Arc<dyn Array>(?)"
        
        # For concrete PrimitiveArray types
        if "PrimitiveArray" in type_name:
            # Try to extract length from the buffer
            values = valobj.GetChildMemberWithName("values")
            if values.IsValid():
                buffer = values.GetChildMemberWithName("buffer")
                if buffer.IsValid():
                    length = buffer.GetChildMemberWithName("length")
                    if length.IsValid():
                        return f"PrimitiveArray(len={length.GetValueAsUnsigned(0)})"
            return "PrimitiveArray(?)"
        
        return f"Array({type_name})"
    except Exception as e:
        return f"Array(error: {e})"

def __lldb_init_module(debugger, internal_dict):
    print("DEBUG: __lldb_init_module called")
    
    # CRITICAL: Import __main__ so the namespace is available
    debugger.HandleCommand('script import __main__')
    
    # Inject function into __main__
    import __main__
    __main__.arrow_array_summary = arrow_array_summary
    
    import time
    time.sleep(0.1)
    
    # Register formatters
    debugger.HandleCommand(
        'type summary add -F __main__.arrow_array_summary '
        '-x "^alloc::sync::Arc<dyn arrow_array::array::Array.*>$" '
        '-w arrow-rs'
    )
    
    debugger.HandleCommand(
        'type summary add -F __main__.arrow_array_summary '
        '-x "^arrow_array::array::.*Array.*$" '
        '-w arrow-rs'
    )
    
    debugger.HandleCommand('type category enable arrow-rs')
    
    print("Arrow-rs formatters loaded")