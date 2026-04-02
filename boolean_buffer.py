import lldb

class BooleanBufferSyntheticChildProvider:
    def __init__(self, valobj: lldb.SBValue, internal_dict):
        self.valobj = valobj
        self.update()
        pass

    def num_children(self, max_children: int) -> int:
        return self.length

    def get_child_index(self, name: str) -> int:
        try:
            return int(name.lstrip('[').rstrip(']'))
        except:
            return -1

    def get_child_at_index(self, index: int) -> lldb.SBValue | None:
        try:
            if index < 0 or index >= self.num_children(4294967295):
                return None
            
            # Read the value from the buffer at this index
            offset = index // 8
            addr = self.ptr + offset
            num_bytes = 1

            # Read memory from the process at the specified address
            error = lldb.SBError()
            # Get the process associated with the target
            target = self.valobj.GetTarget()
            process = target.GetProcess()
            data = process.ReadMemory(addr, num_bytes, error)

            if error.Success():
                byte = data[0]  # Extract the byte
                bit_mask = 1 << index % 8
                is_valid = byte & bit_mask != 0
                child_name = f"[{index}]"  # Correct definition of child_name as a string
                type_str = "bool"
                child_value = "true" if is_valid else "false"
                # Create an SBValue for the boolean result
                return self.valobj.CreateValueFromExpression(child_name, f"({type_str}) {child_value}")
            else:
                print(f"Failed to read memory at address {hex(addr)}: {error.GetCString()}")

        except Exception as e:
            print(f"exception happen making child {e}")
            return None

    def update(self) -> bool:
        try:
            
            buffer = self.valobj.GetChildMemberWithName("buffer")
            if not buffer.IsValid():
                print("ERROR NullBufferSyntheticChildProvider::update buffer not valid")

            ptr_obj = buffer.GetChildMemberWithName("ptr")
            if not ptr_obj.IsValid():
                print("ERROR ptr not valid")
            self.ptr = ptr_obj.GetValueAsUnsigned(0)

            len_obj = self.valobj.GetChildMemberWithName("bit_len")
            if not len_obj.IsValid():
                print("ERROR len not valid")
            self.length = len_obj.GetValueAsUnsigned(0)

        except Exception as e:
            print(f"ERROR NullBufferSyntheticChildProvider::update error happened {e}")
            pass

    def has_children(self) -> bool:
        return True


    # def get_value(self) -> lldb.SBValue | None:
