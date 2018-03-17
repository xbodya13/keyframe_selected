bl_info = {
"name": "Keyframe selected",
"category": "Animation",
"version": (1, 0),
"blender": (2, 7, 9),
"location": "Right click menu",
"description": "Insert or delete keyframes for current UI-active property on selected objects or bones",
"wiki_url": "https://github.com/xbodya13/keyframe_selected",
"tracker_url": "https://github.com/xbodya13/keyframe_selected/issues"
}


import bpy


class Base:
    @classmethod
    def poll(self, context):
        is_animatable = False
        if hasattr(context, 'button_prop'):
            if context.button_prop.is_animatable:
                is_animatable = True

        return is_animatable and context.mode != 'EDIT_ARMATURE' and bpy.ops.ui.copy_to_selected_button.poll()

    @classmethod
    def draw_poll(self,context):
        return context.mode != 'EDIT_ARMATURE' and bpy.ops.ui.copy_to_selected_button.poll()

    def perform(self,mode, context):
        id = None
        path_from_id = None

        button_pointer = None

        if hasattr(context, 'button_prop'):
            if context.button_prop.is_animatable:
                id = context.button_prop.identifier

        if hasattr(context, 'button_pointer'):
            button_pointer = context.button_pointer
            try:
                path_from_id = context.button_pointer.path_from_id(id)
            except:
                pass

        selected_items = context.selected_objects
        data_path = path_from_id

        if context.mode == 'POSE':
            if type(button_pointer) == bpy.types.PoseBone:
                selected_items = context.selected_pose_bones
            if type(button_pointer) == bpy.types.Bone:
                selected_items = [context.object.data.bones[pose_bone.name] for pose_bone in
                                  context.selected_pose_bones]
            data_path = id


        for selected_item in selected_items:
            try:
                if mode == 'INSERT':
                    selected_item.keyframe_insert(data_path)
                if mode == 'DELETE':
                    selected_item.keyframe_delete(data_path)
                if mode == 'CLEAR':
                    if context.mode == 'POSE':
                        if type(button_pointer) == bpy.types.PoseBone:
                            animation_data = context.object.animation_data
                        if type(button_pointer) == bpy.types.Bone:
                            animation_data = context.object.data.animation_data
                        if animation_data != None:
                            to_remove = [fcurve for fcurve in animation_data.action.fcurves if
                                         fcurve.data_path == selected_item.path_from_id(id)]
                            for fcurve in to_remove:
                                animation_data.action.fcurves.remove(fcurve)
                    else:
                        animation_data = selected_item.animation_data
                        if animation_data != None:
                            to_remove = [fcurve for fcurve in animation_data.action.fcurves if
                                         fcurve.data_path == data_path]
                            for fcurve in to_remove:
                                animation_data.action.fcurves.remove(fcurve)
            except:
                pass

        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

class InsertKeyframeSelected(Base,bpy.types.Operator):
    """Insert keyframe for current UI-active property on selected objects"""
    bl_idname = "anim.keyframe_insert_selected_objects_button"
    bl_label = "Insert keyframe (selected)"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        self.perform('INSERT',context)
        return {'FINISHED'}

class DeleteKeyframeSelected(Base,bpy.types.Operator):
    """Delete current keyframe for current UI-active property on selected objects"""
    bl_idname = "anim.keyframe_delete_selected_objects_button"
    bl_label = "Delete keyframe (selected)"
    bl_options = {'REGISTER', 'UNDO'}



    def execute(self, context):
        self.perform('DELETE', context)
        return {'FINISHED'}


class ClearKeyframeSelected(Base,bpy.types.Operator):
    """Clear all keyframes on the currently active property for selected objects"""
    bl_idname = "anim.keyframe_clear_selected_objects_button"
    bl_label = "Clear keyframes (selected)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.perform('CLEAR', context)
        return {'FINISHED'}



# This class has to be exactly named like that to insert an entry in the right click menu
class WM_MT_button_context(bpy.types.Menu):
    bl_label = "Unused"

    def draw(self, context):
        pass

def draw_key(self, context):
    if Base.draw_poll(context):
        layout = self.layout
        layout.separator()
        layout.operator(InsertKeyframeSelected.bl_idname,icon='KEY_HLT')
        layout.operator(DeleteKeyframeSelected.bl_idname)
        layout.operator(ClearKeyframeSelected.bl_idname, icon='KEY_DEHLT')


def register():
    bpy.utils.register_module(__name__)
    bpy.types.WM_MT_button_context.append(draw_key)



def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.WM_MT_button_context.remove(draw_key)



if __name__ == "__main__":
    register()
