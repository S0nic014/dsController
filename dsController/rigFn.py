import pymel.core as pm
from pymel.core import nodetypes
import pymel.api as pma
import json


def isController(obj):
    """
    Checks if given object is a controller (has a controller tag node attached).

    :param obj: object to check
    :type obj: str or PyNode
    :return: True if object is controller, False if not.
    :rtype: bool
    """
    return pm.controller(obj, q=1, ic=1)


def isIKFKLimb(ctl):
    if not isController(ctl):
        return False
    if pm.hasAttr(ctl, "mp"):
        if pm.listConnections(ctl + ".mp"):
            metaNode = pm.listConnections(ctl + ".mp")[0]
            return pm.hasAttr(metaNode, "state")
    else:
        return False


def isMainControl(ctl):
    if ctl.find("C_masterWalk_CTL") != -1 or ctl.find("C_characterNode_CTL") != -1:
        return True
    else:
        return False


# IKFK
def matchFkIk(metaNode=None, *args):
    if not metaNode:
        selection = pm.ls(sl=1)
        if not selection or not pm.hasAttr(selection[-1], "mp"):
            return
        ctl = selection[-1]
        # Try get control module
        metaNode = pm.listConnections(ctl + ".mp")[0]
        if not metaNode:
            return

    if not pm.hasAttr(metaNode, "state"):
        return

    # Get controls and joint chains
    fkControls = getLimbFkControls(metaNode)
    ikChain = getJointChain(pm.getAttr(metaNode + ".ChainIK"))
    fkChain = getJointChain(pm.getAttr(metaNode + ".ChainFK"))
    ikControl = pm.listConnections(metaNode + ".IK")[0]
    poleVector = pm.listConnections(metaNode + ".poleVector")
    state = pm.listConnections(metaNode + ".state", plugs=True)[0]

    # SWITCHING
    # If in FK -> match IK to FK and switch to IK
    if not pm.getAttr(state):
        pm.setAttr(state, 1)
        pm.matchTransform(ikControl, fkChain[2], rot=1, pos=1)
        # Pole vector
        poleLoc = getPoleVector(fkChain[0], fkChain[1], fkChain[2])
        pm.matchTransform(poleVector, poleLoc)
        pm.delete(poleLoc)
        pm.select(cl=1)
    else:
        # If in IK -> match FK to IK and switch to FK
        pm.setAttr(state, 0)
        for ikJnt, fkCtl in zip(ikChain, fkControls):
            pm.matchTransform(fkCtl, ikJnt, rot=1)
        pm.select(cl=1)


def getLimbFkControls(metaNode, *args):
    fkControls = []
    if metaNode:
        for attr in ["ShoulderFK", "HipFK"]:
            if pm.hasAttr(metaNode, attr):
                fkControls.append(pm.listConnections(metaNode + "." + attr)[0])
        for attr in ["ElbowFK", "KneeFK"]:
            if pm.hasAttr(metaNode, attr):
                fkControls.append(pm.listConnections(metaNode + "." + attr)[0])
        for attr in ["WristFK", "AnkleFK"]:
            if pm.hasAttr(metaNode, attr):
                fkControls.append(pm.listConnections(metaNode + "." + attr)[0])
        for attr in ["FootFK"]:
            if pm.hasAttr(metaNode, attr):
                fkControls.append(pm.listConnections(metaNode + "." + attr)[0])
    return fkControls


def getJointChain(firstJoint):
    """
    Gets a joint chain from top most joint

    Args:
        firstJoint (joint): Top most joint in the joint chain

    Returns:
        list: jointchain
    """
    assert pm.nodeType(firstJoint) == 'joint', "Argument {} is not a joint!".format(firstJoint)
    jointChain = [pm.PyNode(firstJoint)]

    for jnt in jointChain:
        if pm.listRelatives(jnt, c=True, type='joint'):
            jointChain += pm.listRelatives(jnt, c=True, type='joint')

    return jointChain


def to_bind_pose(ctl_list, *args):
    for ctl in ctl_list:
        if isController(ctl):
            try:
                bindPose = pm.getAttr(ctl + ".bindPose")
                bindPose = json.loads(bindPose)
                for attr in bindPose.keys():
                    pm.setAttr(ctl + "." + attr, bindPose[attr])
            except RuntimeError:
                continue
        else:
            continue


def revert_selection_bind_pose(*args):
    sel = pm.ls(sl=1)
    to_bind_pose(sel)


def revert_asset_bind_pose(*args):
    sel = pm.ls(sl=1)
    if not sel:
        pm.warning("Select characterNode_CTL for this operation!")
        return
    ctl = sel[-1]
    if not isMainControl(ctl):
        pm.warning("Select characterNode_CTL for this operation!")
        return
    ctl_list = list_character_controls(ctl)
    to_bind_pose(ctl_list)


def getCharacterMeta(ctl):
    if "C_characterNode_CTL" not in str(ctl):
        return None

    connectedNodes = pm.listConnections(ctl.metaParent, s=1)
    try:
        characterMeta = connectedNodes[0]
    except IndexError:
        raise IndexError

    return characterMeta


def getModules(characterMeta, body=False, face=False):
    modules = []
    if body:
        modules += pm.listConnections(characterMeta + ".bodyModules", source=True)

    if face:
        modules += pm.listConnections(characterMeta + ".faceModules", source=True)

    return modules


def getModuleControlSet(module):
    return pm.listConnections(module + ".controlSets")


def list_character_controls(character_node_ctl):
    ctls = []
    meta_node = getCharacterMeta(character_node_ctl)
    modules = getModules(meta_node, body=1, face=1)
    for mod in modules:
        ctls += getModuleControlSet(mod)
    return ctls


def switch_fkik(matching=False):
    ctl = pm.ls(sl=1)[-1]
    mod = ctl.metaParent.listConnections()[0]
    switch_plug = mod.state.listConnections(d=1, plugs=True)[0]
    state = round(mod.state.get())
    if matching:
        matchFkIk(mod)
    else:
        if not state:
            state = 1.0
        else:
            state = 0.0
        switch_plug.set(state)


def switch_space(index, matching=True, keyframe=False, keyframe_offset=-1):
    sel = pm.ls(sl=1)
    if not sel or index < 0:
        return
    ctl = sel[-1]  # type: nodetypes.Transform
    if not ctl.hasAttr("space"):
        pm.error("Missing space attr on {0}".format(ctl))
        return

    # Set keyframe before switch
    if matching and keyframe:
        ctl.space.setKey(t=pm.currentTime() + keyframe_offset)

    old_mtx = ctl.getMatrix(worldSpace=True)
    ctl.space.set(index)
    # Apply saved matrix and create keyframe
    if matching:
        ctl.setMatrix(old_mtx, worldSpace=True)
        if keyframe:
            ctl.space.setKey(t=pm.currentTime())


def set_fkik_blend(value):
    sel = pm.ls(sl=1)
    if not sel or not isIKFKLimb(sel[-1]):
        return
    mod = sel[-1].metaParent.listConnections()[0]
    switch_plug = mod.state.listConnections(d=1, plugs=True)[0]

    switch_plug.set(value)


def get_fkik_state(ctl):
    metaNode = pm.listConnections(ctl + ".mp")[0]
    fkikAttr = pm.listConnections(metaNode + ".state", plugs=True)[0]
    return fkikAttr.get()


def getPoleVector(rootJnt, midJnt, endJnt):
    poleLocator = pm.spaceLocator(n="poleLocator")
    rootJointVec = rootJnt.getTranslation(space="world")  # type:pma.MVector
    midJointVec = midJnt.getTranslation(space="world")  # type:pma.MVector
    endJointVec = endJnt.getTranslation(space="world")  # type:pma.MVector

    # Get projection vector
    line = (endJointVec - rootJointVec)
    closestPoint = (midJointVec - rootJointVec)
    scaleValue = (line * closestPoint) / (line * line)
    projectVec = line * scaleValue + rootJointVec

    # Get chain length
    rootToMidLen = (midJointVec - rootJointVec).length()
    midToEndLen = (endJointVec - midJointVec).length()
    totalLen = rootToMidLen + midToEndLen

    poleVecPosition = (midJointVec - projectVec).normal() * totalLen + midJointVec
    poleLocator.translate.set(poleVecPosition)
    return poleLocator
