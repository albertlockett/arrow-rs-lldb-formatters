import lldb

def arrow_array_summary(valobj, internal_dict):
    type_name = valobj.GetTypeName()
    
    try:
        if type_name.startswith("alloc::sync::Arc"):
            return "Arc<dyn Array>"
        
        if "PrimitiveArray" in type_name:
            import re
            match = re.search(r'PrimitiveArray<.*::(\w+)Type>', type_name)
            elem_type = match.group(1) if match else "?"
            
            values = valobj.GetChildMemberWithName("values")
            if values.IsValid():
                buffer = values.GetChildMemberWithName("buffer")
                if buffer.IsValid():
                    length = buffer.GetChildMemberWithName("length")
                    if length.IsValid():
                        len_val = length.GetValueAsUnsigned(0)
                        
                        nulls = valobj.GetChildMemberWithName("nulls")
                        null_count = 0
                        if nulls.IsValid():
                            null_count_field = nulls.GetChildMemberWithName("null_count")
                            if null_count_field.IsValid():
                                null_count = null_count_field.GetValueAsUnsigned(0)
                        
                        if null_count > 0:
                            return f"PrimitiveArray<{elem_type}>(len={len_val}, nulls={null_count})"
                        else:
                            return f"PrimitiveArray<{elem_type}>(len={len_val})"
            
            return f"PrimitiveArray<{elem_type}>(?)"
        
        return f"Array"
    except Exception as e:
        return f"Array(error: {e})"

def scalar_buffer_summary(valobj, internal_dict):
    """Formatter for ScalarBuffer<T>"""
    type_name = valobj.GetTypeName()
    
    try:
        # Extract element type
        import re
        match = re.search(r'ScalarBuffer<(.+)>', type_name)
        elem_type = match.group(1) if match else "?"
        
        # Get length from buffer
        buffer = valobj.GetChildMemberWithName("buffer")
        if buffer.IsValid():
            length = buffer.GetChildMemberWithName("length")
            ptr = buffer.GetChildMemberWithName("ptr")
            
            if length.IsValid() and ptr.IsValid():
                len_val = length.GetValueAsUnsigned(0)
                ptr_val = ptr.GetValueAsUnsigned(0)
                return f"ScalarBuffer<{elem_type}>(len={len_val}, ptr=0x{ptr_val:x})"
        
        return f"ScalarBuffer<{elem_type}>(?)"
    except Exception as e:
        return f"ScalarBuffer(error: {e})"

def arrow_buffer_summary(valobj, internal_dict):
    """Formatter for immutable::Buffer"""
    try:
        length = valobj.GetChildMemberWithName("length")
        ptr = valobj.GetChildMemberWithName("ptr")
        
        if length.IsValid() and ptr.IsValid():
            len_val = length.GetValueAsUnsigned(0)
            ptr_val = ptr.GetValueAsUnsigned(0)
            return f"Buffer(len={len_val}, ptr=0x{ptr_val:x})"
        
        return "Buffer(?)"
    except Exception as e:
        return f"Buffer(error: {e})"



class PrimitiveArraySyntheticProvider:
    """Synthetic children provider to show array elements"""
    
    def __init__(self, valobj, internal_dict):
        self.valobj = valobj
        self.update()
    
    def num_children(self):
        return min(self.length, 100)  # Cap at 100 for performance
    
    def get_child_index(self, name):
        try:
            return int(name.lstrip('[').rstrip(']'))
        except:
            return -1
    
    def get_child_at_index(self, index):
        if index < 0 or index >= self.num_children():
            return None
        
        try:
            # Read the value from the buffer at this index
            offset = index * self.elem_size
            addr = self.ptr + offset
            
            # Create a value object for this element
            return self.valobj.CreateValueFromAddress(
                f"[{index}]",
                addr,
                self.elem_type
            )
        except:
            return None
    
    def update(self):
        """Extract buffer pointer, length, and element type"""
        try:
            # Get the element type from PrimitiveArray<T>
            type_name = self.valobj.GetTypeName()
            
            # Map Arrow types to LLDB types
            type_map = {
                'UInt8Type': 'uint8_t',
                'UInt16Type': 'uint16_t',
                'UInt32Type': 'uint32_t',
                'UInt64Type': 'uint64_t',
                'Int8Type': 'int8_t',
                'Int16Type': 'int16_t',
                'Int32Type': 'int32_t',
                'Int64Type': 'int64_t',
                'Float32Type': 'float',
                'Float64Type': 'double',
            }
            
            import re
            match = re.search(r'PrimitiveArray<.*::(\w+)>', type_name)
            if match:
                arrow_type = match.group(1)
                lldb_type_name = type_map.get(arrow_type, 'uint8_t')
            else:
                lldb_type_name = 'uint8_t'
            
            # Get the type object from the target
            target = self.valobj.GetTarget()
            self.elem_type = target.FindFirstType(lldb_type_name)
            self.elem_size = self.elem_type.GetByteSize()
            
            # Navigate to the buffer pointer and length
            values = self.valobj.GetChildMemberWithName("values")
            buffer = values.GetChildMemberWithName("buffer")
            
            self.ptr = buffer.GetChildMemberWithName("ptr").GetValueAsUnsigned(0)
            self.length = buffer.GetChildMemberWithName("length").GetValueAsUnsigned(0)
            
        except Exception as e:
            print(f"PrimitiveArray synthetic update error: {e}")
            self.ptr = 0
            self.length = 0
            self.elem_size = 1
            self.elem_type = None
    
    def has_children(self):
        return True

def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('script import __main__')
    
    import __main__
    __main__.arrow_array_summary = arrow_array_summary
    __main__.scalar_buffer_summary = scalar_buffer_summary
    __main__.arrow_buffer_summary = arrow_buffer_summary
    __main__.PrimitiveArraySyntheticProvider = PrimitiveArraySyntheticProvider
    
    import time
    time.sleep(0.1)
    
    # Array formatters (summaries)
    debugger.HandleCommand(
        'type summary add -F __main__.arrow_array_summary '
        '-x "^alloc::sync::Arc<dyn arrow_array::array::Array.*>$" '
        '-w arrow-rs'
    )
    
    # PrimitiveArray: add BOTH summary and synthetic
    debugger.HandleCommand(
        'type summary add -F __main__.arrow_array_summary '
        '-x "^arrow_array::array::primitive_array::PrimitiveArray<.*>$" '
        '-w arrow-rs '
        '-e'  # <-- expand inline (show summary + children)
    )
    
    debugger.HandleCommand(
        'type synthetic add '
        '-x "^arrow_array::array::primitive_array::PrimitiveArray<.*>$" '
        '-w arrow-rs '
        '-l __main__.PrimitiveArraySyntheticProvider'
    )
    
    # Buffer formatters
    debugger.HandleCommand(
        'type summary add -F __main__.scalar_buffer_summary '
        '-x "^arrow_buffer::buffer::scalar::ScalarBuffer<.*>$" '
        '-w arrow-rs'
    )
    
    debugger.HandleCommand(
        'type summary add -F __main__.arrow_buffer_summary '
        '"arrow_buffer::buffer::immutable::Buffer" '
        '-w arrow-rs'
    )
    
    debugger.HandleCommand('type category enable arrow-rs')
    print("Arrow-rs formatters loaded")