
import lldb

def get_array_concrete_type_from_vtable(valobj):
    try:
        raw_val = valobj.GetNonSyntheticValue()
        ptr_val = raw_val.GetChildMemberWithName("ptr")
        pointer_val = ptr_val.GetChildMemberWithName("pointer")
        vtable_val = pointer_val.GetChildMemberWithName("vtable")
        vtable_pointer = vtable_val.GetValueAsUnsigned()

        target = valobj.GetTarget()
        process = target.GetProcess()
        error = lldb.SBError()
        first_fn_ptr = process.ReadPointerFromMemory(vtable_pointer, error)
        
        if error.Success():
            sb_addr = target.ResolveLoadAddress(first_fn_ptr)
            symbol = sb_addr.GetSymbol()
            
            if symbol and symbol.IsValid():
                symbol_name = symbol.GetName()
                # Symbol typically: core::ptr::drop_in_place<arrow_array::array::primitive_array::PrimitiveArray<...>>
                # Use regex to extract the type inside the brackets
                import re
                match = re.search(r'drop_in_place<(.*)>', symbol_name)
                if match:
                    return match.group(1)
        
        return None
    except Exception as e:
        print(f"ERROR get_array_concrete_type_from_vtable error: {e}")
        import traceback
        traceback.print_exc()
        return None
    
def array_ref_summary(valobj, internal_dict):
    concrete_type = get_array_concrete_type_from_vtable(valobj)
    print(f"DEBUG concrete array ref type = {concrete_type}")
    return f"Arc<{concrete_type} as dyn Array>"

class ArrayRefSyntheticChildProvider:
    def __init__(self, valobj: lldb.SBValue, internal_dict):
        self.valobj = valobj
        self.update()

    def num_children(self, max_children: int) -> int:
      return 1

    def get_child_index(self, name: str) -> int:
      return 0

    def get_child_at_index(self, index: int) -> lldb.SBValue | None:
        try:
           return self.valobj.CreateValueFromAddress(
               "data",
               self.ptr,
               self.concrete_type
           )
        except Exception as e:
           print(f"ERROR exception happen making child {e}")
           return None

    def update(self) -> bool:
        try:
            self.concrete_type_name = get_array_concrete_type_from_vtable(self.valobj)

            target = self.valobj.GetTarget()
            self.concrete_type = target.FindFirstType(self.concrete_type_name)
            if not self.concrete_type.IsValid():
                print("ERROR type not valid")

            raw_val = self.valobj.GetNonSyntheticValue()
            ptr_val = raw_val.GetChildMemberWithName("ptr")
            if not ptr_val.IsValid():
                print(f"ERROR ptr_val not valid")

            ptr_val = ptr_val.GetChildMemberWithName("pointer")
            if not ptr_val.IsValid():
                print(f"ERROR pointer not valid")

            inner_pointer = ptr_val.GetChildMemberWithName("pointer")
            if not inner_pointer.IsValid():
                print(f"ERROR inner_pointer not valid")
            
            # self.ptr = inner_pointer.GetValueAsUnsigned(0);
            # print(f"DEBUG self.ptr = {self.ptr:x}")

            arc_inner_data = inner_pointer.GetChildMemberWithName("data")
            # print(f"inner arg data = {arc_inner_data} is valid = {arc_inner_data.IsValid()}")
            self.ptr = arc_inner_data.GetAddress().GetLoadAddress(target)
            
        except Exception as e:
            print(f"ERROR calling update {e}")

    def has_children(self) -> bool:
      return True

