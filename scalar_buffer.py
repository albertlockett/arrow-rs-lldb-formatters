import lldb

def scalar_buffer_array_summary(valueobj, internal_dict):
    return "test"

class ScalarBufferSyntheticChildProvider:
    def __init__(self, valobj: lldb.SBValue, internal_dict):
        print("synthetic child called")
        self.valobj = valobj
        self.update()

    def num_children(self, max_children: int) -> int:
        print(f"max children {max_children}")
        return min(self.length, max_children)

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
            offset = index * self.elem_size
            addr = self.ptr + offset

            # Create a value object for this element
            return self.valobj.CreateValueFromAddress(
                f"[{index}]",
                addr,
                self.elem_type
            )
        except Exception as e:
            print(f"exception happen making child {e}")
            return None

    def has_children(self) -> bool:
        True
    
    def update(self):
        try:
            type_name = self.valobj.GetTypeName()
            type_to_size = {
                'unsigned char': 1,
                'unsigned short': 2,
            }

            import re
            match = re.search(r'.*ScalarBuffer<(.+)>', type_name)
            if match:
                lldb_type_name = match.group(1)
                self.elem_size = type_to_size.get(lldb_type_name)
            else:
                print("ERROR no match")

            target = self.valobj.GetTarget()
            self.elem_type = target.FindFirstType(lldb_type_name)
            if not self.elem_type.IsValid():
                print("ERROR type not valid")

            buffer = self.valobj.GetChildMemberWithName("buffer")
            if not buffer.IsValid():
                print("ERROR buffer not valid")
            
            ptr_obj = buffer.GetChildMemberWithName("ptr")
            len_obj = buffer.GetChildMemberWithName("length")
            if not ptr_obj.IsValid():
                print("ERROR ptr not valid")
            if not len_obj.IsValid():
                print("ERROR len not valid")

            self.ptr = ptr_obj.GetValueAsUnsigned(0)
            self.length = len_obj.GetValueAsUnsigned(0) // self.elem_size

        except Exception as e:
            print(f"ERROR error happened {e}")
            pass

#    def get_value(self) -> lldb.SBValue | None:
#       """
#       This call can return an SBValue to be presented as the value of the
#       synthetic value under consideration.[4]
#       """"