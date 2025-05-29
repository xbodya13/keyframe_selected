import math


bl_info = {
"name": "Keyframe selected",
"category": "Animation",
"version": (1, 3),
"blender": (4, 4, 0),
"location": "Right click menu",
"description": "Insert or delete keyframes for current UI-active property on selected objects or bones",
"wiki_url": "https://github.com/xbodya13/keyframe_selected",
"tracker_url": "https://github.com/xbodya13/keyframe_selected/issues"
}


import bpy
from bpy.app.handlers import persistent
import numpy as np
from mathutils import Vector



class gv:
    keyconfig=None

    last_animation_data=None

    track_pose_bones=[]
    track_objects=[]

    color_data={}

    is_color_update=False

def get_add_color(item):
    return Vector((*bpy.context.preferences.themes[0].user_interface.wcol_state.inner_key,1))

def get_remove_color(item):
    if type(item) is bpy.types.PoseBone:
        color, _, _, _ = get_bone_colors(item)
    else:
        color=Vector(item.color)

    color*= 0.8
    color[3] = 1

    return color


def get_bone_colors(bone):
    theme=bpy.context.preferences.themes[0]
    palette=bone.color.palette
    if palette=='DEFAULT':
        normal=theme.view_3d.bone_solid
        select=theme.view_3d.bone_pose
        active=theme.view_3d.bone_pose_active

        show_colored_constraints=True
    elif palette=='CUSTOM':
        normal=bone.color.custom.normal
        select=bone.color.custom.select
        active=bone.color.custom.active
        show_colored_constraints=bone.color.custom.show_colored_constraints
    else:
        place=int(palette[-2:])-1


        normal=theme.bone_color_sets[place].normal
        select=theme.bone_color_sets[place].select
        active=theme.bone_color_sets[place].active

        show_colored_constraints=theme.bone_color_sets[place].show_colored_constraints

    # print(normal,select,active)

    normal=Vector((*normal,1))
    select=Vector((*select,1))
    active=Vector((*active,1))

    return normal,select,active,show_colored_constraints




def get_signature(item):
    if type(item) is bpy.types.PoseBone:
        return item.id_data.name,item.name
    else:
        return item.name,None



class ColorRecord:
    def __init__(self,item,target_color):



        if type(item) is bpy.types.PoseBone:
            self.is_bone=True
            self.name=item.id_data.name
            self.bone_name=item.name

            self.start_palette=item.color.palette
            self.start_normal=Vector(item.color.custom.normal)
            self.start_select=Vector(item.color.custom.select)
            self.start_active=Vector(item.color.custom.active)
            self.start_show_colored_constraints=item.color.custom.show_colored_constraints



            normal, select, active, show_colored_constraints=get_bone_colors(item)

            self.base_normal=Vector(normal)
            self.base_select=Vector(select)
            self.base_active=Vector(active)
            self.base_show_colored_constraints=show_colored_constraints


            start_color=Vector(normal)

        else:
            self.is_bone = False
            self.name=item.id_data.name
            self.bone_name=None

            self.start_color=Vector(item.color)

            start_color = Vector(item.color)


        # target_color=Vector((1,0,0,1))

        self.signature=get_signature(item)

        self.is_done=False


        self.color_line = []

        count=10
        step=1/(count-1)
        for x in range(count):
            factor=x*step

            # factor=(-factor+1)**3

            # factor=1-math.exp(-(factor-0.)**4)

            factor=(-math.cos(factor*math.pi)/2+0.5)**2


            color=target_color*(1-factor)+start_color*factor
            self.color_line.append(color)



    def __str__(self):return f"{len(self.color_line)} "

    def __repr__(self):return str(self)

    def get_item(self):
        item=None
        if self.name in bpy.data.objects:
            if self.is_bone:
                if self.bone_name in bpy.data.objects[self.name].pose.bones:
                    item=bpy.data.objects[self.name].pose.bones[self.bone_name]
            else:
                item=bpy.data.objects[self.name]

        return item



    def step(self):
        item = self.get_item()
        if item is None:self.is_done=True
        else:
            if len(self.color_line)!=0:
                color=self.color_line.pop(0)

                if self.is_bone:
                    item.color.palette='CUSTOM'
                    item.color.custom.normal=color[:3]
                    item.color.custom.select=self.base_select[:3]
                    item.color.custom.active=self.base_active[:3]
                    item.color.custom.show_colored_constraints=self.base_show_colored_constraints

                else:
                    item.color=color

            if len(self.color_line)==0:
                self.reset()
                self.is_done=True

    def reset(self):
        item=self.get_item()
        if item is not None:
            if self.is_bone:
                item.color.palette=self.start_palette
                item.color.custom.normal=self.start_normal
                item.color.custom.select=self.start_select
                item.color.custom.active=self.start_active
                item.color.custom.show_colored_constraints=self.start_show_colored_constraints
            else:
                item.color=self.start_color

class Base:
    @classmethod
    def poll(self, context):
        is_animatable = False
        if hasattr(context, 'button_prop'):
            if context.button_prop.is_animatable:
                is_animatable = True

        # is_animatable=True

        return is_animatable and context.mode != 'EDIT_ARMATURE' and bpy.ops.ui.copy_to_selected_button.poll()

    @classmethod
    def draw_poll(self,context):
        return context.mode != 'EDIT_ARMATURE' and bpy.ops.ui.copy_to_selected_button.poll()

    def perform(self,mode, context):
        def fcurve_iterator(animation_data):
            if animation_data.action is not None:
                for layer in animation_data.action.layers:
                    for strip in layer.strips:
                        for channelbag in strip.channelbags:
                            fcurves=channelbag.fcurves
                            for fcurve in channelbag.fcurves:
                                yield fcurves,fcurve


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



        get_item = lambda source: source
        if context.mode in  ('OBJECT',) and hasattr(button_pointer,"id_data") and type(button_pointer.id_data) != bpy.types.Object:
            # print("AAA")
            get_item=lambda source:source.data



        selected_items = context.selected_objects
        data_path = path_from_id

        # print(type(button_pointer))
        if context.mode == 'POSE' and type(button_pointer) in  (bpy.types.PoseBone,bpy.types.Bone):

            selected_items = context.selected_pose_bones
            if type(button_pointer) == bpy.types.Bone:
                get_item = lambda source: source.bone

            data_path = id


        # print(selected_items)


        do_color_update=False

        for selected_item in selected_items:

            # selected_item=get_item(selected_item)

            change=False
            try:
                if mode == 'INSERT':
                    change=get_item(selected_item).keyframe_insert(data_path)
                if mode == 'DELETE':
                    change=get_item(selected_item).keyframe_delete(data_path)
                if mode == 'CLEAR':
                    if context.mode == 'POSE' and type(button_pointer) in  (bpy.types.PoseBone,bpy.types.Bone):
                        if type(button_pointer) == bpy.types.PoseBone:
                            animation_data = context.object.animation_data
                        if type(button_pointer) == bpy.types.Bone:
                            animation_data = context.object.data.animation_data

                        if not "4.3":
                            if animation_data != None:
                                to_remove = [fcurve for fcurve in animation_data.action.fcurves if fcurve.data_path == get_item(selected_item).path_from_id(id)]

                                for fcurve in to_remove:
                                    animation_data.action.fcurves.remove(fcurve)
                                    change = True

                        if  "4.4":

                            if animation_data != None:
                                to_remove = [(fcurves,fcurve) for fcurves,fcurve in fcurve_iterator(animation_data) if fcurve.data_path == get_item(selected_item).path_from_id(id)]


                                for fcurves,fcurve in to_remove:
                                    fcurves.remove(fcurve)
                                    change = True


                    else:
                        animation_data = get_item(selected_item).animation_data
                        if animation_data != None:
                            to_remove = [(fcurves, fcurve) for fcurves, fcurve in fcurve_iterator(animation_data) if fcurve.data_path == data_path]


                            for fcurves,fcurve in to_remove:
                                    fcurves.remove(fcurve)
                                    change = True




            except:pass

            # print(change)

            if change:
                if mode=='INSERT':color=get_add_color(selected_item)
                else:color=get_remove_color(selected_item)

                signature = get_signature(selected_item)

                if signature in gv.color_data:
                    gv.color_data[signature].reset()
                gv.color_data[signature] = ColorRecord(selected_item, color)

                do_color_update=True



        if do_color_update:
            if not bpy.app.timers.is_registered(color_updater):
                bpy.app.timers.register(color_updater)

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

class Test(bpy.types.Operator):
    """Test"""
    bl_idname="key_selected.test"
    bl_label="Test"
    bl_options={'REGISTER','UNDO'}


    @classmethod
    def poll(self,context):
        return True

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):

        # print(event.alt)


        return {'PASS_THROUGH'}

    def execute(self,context):
        # print("Test")


        return {'FINISHED'}




def get_animation_data():
    # print("GET ANIMATION DATA")
    if not "4.3":
        def fcurve_iterator(holder):
            if holder.animation_data is not None:
                if holder.animation_data.action is not None:
                    for fcurve in holder.animation_data.action.fcurves:
                        for keyframe_point in fcurve.keyframe_points:
                            if keyframe_point.co.x==bpy.context.scene.frame_current:
                                yield fcurve.data_path,fcurve.array_index
    if "4.4":
        def fcurve_iterator(holder):
            # print("FCURVE")
            if holder.animation_data is not None:
                if holder.animation_data.action is not None:
                    for layer in holder.animation_data.action.layers:
                        for strip in layer.strips:
                            for channelbag in strip.channelbags:
                                for fcurve in channelbag.fcurves:
                                    for keyframe_point in fcurve.keyframe_points:
                                        if keyframe_point.co.x==bpy.context.scene.frame_current:
                                            yield fcurve.data_path,fcurve.array_index
                                            break



    def get_relative_path(item, data_path,index):
        other_parts = data_path.split(".")
        out_path=None
        # print(item, other_parts,property_name)

        current_item = item.id_data
        current_path = None
        # print()


        while True:
            # print("    ",current_item,current_path)

            if type(current_item) is type(item):
                out_path = ".".join(other_parts)
                break
            if len(other_parts)==0:break

            part = other_parts.pop(0)

            if current_path is None:current_path=part
            else:current_path=f"{current_path}.{part}"

            try:
                current_item = item.id_data.path_resolve(current_path)
            except ValueError:current_item=None

        out_index=-1
        try:
            item.path_resolve(f"{out_path}[{index}]")
            out_index=index
        except :pass

        return out_path,out_index

    out={}
    if bpy.context.mode == 'POSE':

        fcurve_cache={}


        for item in gv.track_pose_bones:

            source=item.id_data
            if  source not in fcurve_cache:
                fcurve_cache[source]=list(fcurve_iterator(source))
            fcurve_data = fcurve_cache[source]

            for signature_data_path,signature_index in fcurve_data:
                get_item=lambda source:source
                data_path,index=get_relative_path(item, signature_data_path, signature_index)

                if data_path is not None:
                    out[item,signature_data_path,signature_index]=item,get_item,data_path,index


            source=item.bone.id_data
            if  source not in fcurve_cache:
                fcurve_cache[source]=list(fcurve_iterator(source))
            fcurve_data = fcurve_cache[source]

            for signature_data_path, signature_index in fcurve_data:
                get_item = lambda source: source.bone
                data_path, index = get_relative_path(item.bone, signature_data_path, signature_index)

                if data_path is not None:
                    out[item, signature_data_path, signature_index] = item,get_item, data_path, index


        # print(out)

    # else:
    # print(gv.track_objects)
    for item in gv.track_objects:
        for signature_data_path, signature_index in fcurve_iterator(item.id_data):
            get_item = lambda source: source
            data_path, index = get_relative_path(item, signature_data_path, signature_index)
            if data_path is not None:
                out[item, signature_data_path, signature_index] =item,get_item, data_path, index

        if item.data is not None:
            for signature_data_path, signature_index in fcurve_iterator(item.data.id_data):
                get_item = lambda source: source.data
                data_path, index = get_relative_path(item.data, signature_data_path, signature_index)
                if data_path is not None:
                    out[item, signature_data_path, signature_index] =item,get_item, data_path, index

    return out




def color_updater():

    for signature,record in gv.color_data.items():
        record.step()

    gv.color_data={signature:record for signature,record in gv.color_data.items() if not record.is_done}

    # print(gv.color_data)

    if len(gv.color_data)==0:
        gv.is_color_update=False
        return None
    else:
        gv.is_color_update = True
        return 1/30




@persistent
def handler(scene):
    # print("HANDLER")

    if bpy.context.preferences.addons[__name__].preferences.use_animation:

        if gv.is_color_update:
            animation_data=gv.last_animation_data
        else:
            animation_data = get_animation_data()




        if gv.last_animation_data is not None:

            do_color_update=False

            to_add=set()
            to_remove=set()

            keys= {*gv.last_animation_data, *animation_data}

            for key in keys:

                last_state = False
                if key in gv.last_animation_data:
                    last_state=True

                    load =gv.last_animation_data[key]




                state = False
                if key in animation_data:
                    state=True

                    load = animation_data[key]





                if last_state and not state:
                    to_remove.add(load)
                if not last_state and state:
                    to_add.add(load)

            # print()
            # print(to_add)
            # print(to_remove)

            if bpy.context.mode == 'POSE':
                # items = list(bpy.context.selected_pose_bones)+list(bpy.context.selected_objects)
                selected_objects=bpy.context.selected_objects
                selected_pose_bones=bpy.context.selected_pose_bones


            else:
#                 items = bpy.context.selected_objects

                selected_objects=bpy.context.selected_objects
                selected_pose_bones=[]

            # print(to_add)

            if "INSERT":
                for base_item,get_item,data_path,index in to_add:
                    if type(base_item) is bpy.types.PoseBone:items=selected_pose_bones
                    elif type(base_item) is bpy.types.Object: items = selected_objects


                    for item in items:

                        change=False

                        # print(item,data_path)
                        try:
                            get_item(item).path_resolve(data_path)
                            change=True
                            get_item(item).keyframe_insert(data_path,index=index)

                        except:pass


                        if change:
                            signature=get_signature(item)
                            if signature in gv.color_data:
                                gv.color_data[signature].reset()
                            gv.color_data[signature]=ColorRecord(item,get_add_color(item))
                            do_color_update = True

            if "REMOVE":
                for base_item,get_item, data_path, index in to_remove:
                    if type(base_item) is bpy.types.PoseBone:items=selected_pose_bones
                    elif type(base_item) is bpy.types.Object: items = selected_objects
                    for item in items:

                        change = False

                        # print(item,data_path)
                        try:
                            get_item(item).path_resolve(data_path)
                            change=True
                            get_item(item).keyframe_delete(data_path, index=index)
                        except:
                            pass

                        if change:
                            signature = get_signature(item)
                            if signature in gv.color_data:
                                gv.color_data[signature].reset()
                            gv.color_data[signature] = ColorRecord(item, get_remove_color(item))
                            do_color_update = True


            if do_color_update:
                animation_data=get_animation_data()
                if not bpy.app.timers.is_registered(color_updater):
                    bpy.app.timers.register(color_updater)


            # print(gv.last_animation_data)
            # print(animation_data)

        gv.last_animation_data=animation_data







class StartTracking(bpy.types.Operator):
    """Test"""
    bl_idname="key_selected.start_tracking"
    bl_label="Start tracking"
    bl_options={'REGISTER','INTERNAL'}


    @classmethod
    def poll(self,context):
        return bpy.context.preferences.addons[__name__].preferences.use_animation

    def invoke(self, context, event):
        # print("START TRACKING")
        context.window_manager.modal_handler_add(self)

        gv.track_objects=list(bpy.context.selected_objects)
        if bpy.context.mode=='POSE':gv.track_pose_bones=list(bpy.context.selected_pose_bones)
        else:gv.track_pose_bones=[]

        gv.last_animation_data=get_animation_data()
        bpy.app.handlers.depsgraph_update_pre.append(handler)

        return {'RUNNING_MODAL'}

    def modal(self, context, event):

        if not event.alt:
            # print("STOP TRACKING")
            bpy.app.handlers.depsgraph_update_pre.remove(handler)
            return {'FINISHED'}

        return {'PASS_THROUGH'}



    def execute(self,context):
        # print("START TRACKING")


        return {'FINISHED'}

# This class has to be exactly named like that to insert an entry in the right click menu
class WM_MT_button_context(bpy.types.Menu):
    bl_label = "Unused"

    def draw(self, context):
        pass



class Preferences(bpy.types.AddonPreferences):

    bl_idname = __name__


    use_animation: bpy.props.BoolProperty(name="Color animations",default=True)
    use_menu: bpy.props.BoolProperty(name="Extend context menu", default=True)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_animation")
        layout.prop(self, "use_menu")

def draw_key(self, context):
    if Base.draw_poll(context):
        if bpy.context.preferences.addons[__name__].preferences.use_menu:
            layout = self.layout
            layout.separator()
            layout.operator(InsertKeyframeSelected.bl_idname,icon='KEY_HLT')
            layout.operator(DeleteKeyframeSelected.bl_idname)
            layout.operator(ClearKeyframeSelected.bl_idname, icon='KEY_DEHLT')


def setattr_nested(source,path,value):
    splitted=path.split(".")

    out_source=source
    for name in splitted[:-1]:
        if hasattr(out_source,name):
            out_source=getattr(out_source,name)
        else:
            return None
    if hasattr(out_source,splitted[-1]):
        setattr(out_source,splitted[-1],value)


def make_keys():
    # print("MAKE KEYS")

    gv.blanks=(
            ('Window',StartTracking.bl_idname,'LEFT_ALT','PRESS'),
            # ('Window',StopTracking.bl_idname, 'LEFT_ALT', 'RELEASE')
    )

    if bpy.context.window_manager.keyconfigs.active is not None:
        gv.keyconfig=bpy.context.window_manager.keyconfigs.active

    else:
        gv.keyconfig=bpy.context.window_manager.keyconfigs.default
        # print("AAA")

    for keymap,*blank in gv.blanks:
        if keymap not in gv.keyconfig.keymaps:keymap_items=gv.keyconfig.keymaps.new(keymap).keymap_items
        else:keymap_items=gv.keyconfig.keymaps[keymap].keymap_items

        keymap_items.new(*blank, head=False)





def clear_keys():
    # print("CLEAR KEYS")
    to_remove=[]
    if gv.keyconfig is not None:
        for keymap,target_idname,target_type,target_value in gv.blanks:
            if keymap in gv.keyconfig.keymaps:
                keymap_items = gv.keyconfig.keymaps[keymap].keymap_items

                for item in keymap_items:
                    if (target_idname,target_type,target_value)==(item.idname,item.type,item.value):
                        to_remove.append((keymap_items,item))

        for keymap_items,item in to_remove:
            keymap_items.remove(item)
@persistent
def save_pre_handler():
    for record in gv.color_data.values():
        record.reset()


register_classes=[InsertKeyframeSelected,DeleteKeyframeSelected,ClearKeyframeSelected,WM_MT_button_context,StartTracking,Preferences,Test]
def register():
    # bpy.app.handlers.depsgraph_update_pre.append(scene_before_handler)

    bpy.app.handlers.save_pre.append(save_pre_handler)


    for register_class in register_classes:
        bpy.utils.register_class(register_class)
    bpy.types.WM_MT_button_context.append(draw_key)


    make_keys()



def unregister():
    clear_keys()

    bpy.types.WM_MT_button_context.remove(draw_key)

    for register_class in reversed(register_classes):
        bpy.utils.unregister_class(register_class)



    # bpy.app.handlers.depsgraph_update_pre.remove(scene_before_handler)
    bpy.app.handlers.save_pre.remove(save_pre_handler)





