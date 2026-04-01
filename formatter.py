import lldb

def arrow_array_summary(valobj, internal_dict):
    type_name = valobj.GetTypeName()
    
    try:
        if type_name.startswith("alloc::sync::Arc"):
            try:
                raw_val = valobj.GetNonSyntheticValue()
                ptr_val = raw_val.GetChildMemberWithName("ptr")
                print(f"DEBUG ptr_val valid = {ptr_val.IsValid()}")

                pointer_val = ptr_val.GetChildMemberWithName("pointer")
                print(f"DEBUG pointer valid = {pointer_val.IsValid()}")

                vtable_val = pointer_val.GetChildMemberWithName("vtable")
                print(f"DEBUG vtable_val valid = {vtable_val.IsValid()}")

                vtable_pointer = vtable_val.GetValueAsUnsigned()
                print(f"DEBUG: Child[0] addr = 0x{vtable_pointer:x}")

                target = valobj.GetTarget()
                process = target.GetProcess()
                error = lldb.SBError()
                first_fn_ptr = process.ReadPointerFromMemory(vtable_pointer, error)
                
                if error.Success():
                    print("DEBUG symbol no error reading memory from vtable")
                    sb_addr = target.ResolveLoadAddress(first_fn_ptr)
                    symbol = sb_addr.GetSymbol()
                    
                    if symbol and symbol.IsValid():
                        print("DEBUG symbol valid")
                        symbol_name = symbol.GetName()
                        print(f"DEBUG symbol name {symbol_name}")
                        # Symbol typically: core::ptr::drop_in_place<arrow_array::array::primitive_array::PrimitiveArray<...>>
                        # Use regex to extract the type inside the brackets
                        import re
                        match = re.search(r'drop_in_place<(.*)>', symbol_name)
                        if match:
                            print(f"DEBUG match 1 {match.group(1)}")
                            return f"Arc<{match.group(1)} as Array>"
                
                return "Arc<dyn Array>(debug)"
            except Exception as e:
                print(f"DEBUG arc_dyn_array_summary error: {e}")
                import traceback
                traceback.print_exc()
                return f"Arc<dyn Array>(error: {e})"
        
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
            print(f"DEBUG: update() called for {self.valobj.GetTypeName()}")
            
            # Get the element type from PrimitiveArray<T>
            type_name = self.valobj.GetTypeName()
            
            # Map Arrow types to LLDB types and sizes
            type_map = {
                'UInt8Type': ('unsigned char', 1),
                'UInt16Type': ('unsigned short', 2),
                'UInt32Type': ('unsigned int', 4),
                'UInt64Type': ('unsigned long long', 8),
                'Int8Type': ('char', 1),
                'Int16Type': ('short', 2),
                'Int32Type': ('int', 4),
                'Int64Type': ('long long', 8),
                'Float32Type': ('float', 4),
                'Float64Type': ('double', 8),
            }
            
            import re
            match = re.search(r'PrimitiveArray<.*::(\w+)>', type_name)
            if match:
                arrow_type = match.group(1)
                lldb_type_name, self.elem_size = type_map.get(arrow_type, ('unsigned char', 1))
                print(f"DEBUG: Detected type {arrow_type} -> {lldb_type_name}, size {self.elem_size}")
            else:
                lldb_type_name = 'unsigned char'
                self.elem_size = 1
                print(f"DEBUG: No type match, using default")
            
            # Get the type object from the target
            target = self.valobj.GetTarget()
            self.elem_type = target.FindFirstType(lldb_type_name)
            
            if not self.elem_type or not self.elem_type.IsValid():
                print(f"DEBUG: Type {lldb_type_name} not found!")
                self.elem_type = target.FindFirstType('unsigned char')
            else:
                print(f"DEBUG: Found type {lldb_type_name}")
            
            # Navigate to the buffer pointer and length
            values = self.valobj.GetChildMemberWithName("values")
            print(f"DEBUG: values valid: {values.IsValid()}")
            
            buffer = values.GetChildMemberWithName("buffer")
            print(f"DEBUG: buffer valid: {buffer.IsValid()}")
            
            ptr_obj = buffer.GetChildMemberWithName("ptr")
            len_obj = buffer.GetChildMemberWithName("length")
            
            print(f"DEBUG: ptr valid: {ptr_obj.IsValid()}, len valid: {len_obj.IsValid()}")
            
            self.ptr = ptr_obj.GetValueAsUnsigned(0)
            self.length = len_obj.GetValueAsUnsigned(0) // self.elem_size
            
            print(f"DEBUG: ptr=0x{self.ptr:x}, length={self.length}, elem_size={self.elem_size}")
            
        except Exception as e:
            print(f"PrimitiveArray synthetic update error: {e}")
            import traceback
            traceback.print_exc()
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