BONE_MAP = {
    "全ての親": "Root", "センター": "Center", "グルーブ": "Groove",
    "腰": "Waist", "上半身": "UpperBody", "上半身1": "UpperBody1",
    "上半身2": "UpperBody2", "上半身3": "UpperBody3",
    "下半身": "LowerBody", "頭": "Head", "首": "Neck",
    "肩": "Shoulder", "肩C": "ShoulderC", "肩P": "ShoulderP",
    "腕": "Arm", "腕捩": "ArmTwist", "腕捩1": "ArmTwist1",
    "腕捩2": "ArmTwist2", "腕捩3": "ArmTwist3",
    "ひじ": "Elbow", "手首": "Wrist",
    "手捩": "WristTwist", "手捩1": "WristTwist1",
    "手捩2": "WristTwist2", "手捩3": "WristTwist3",
    "足": "Leg", "足D": "LegD",
    "ひざ": "Knee", "ひざD": "KneeD",
    "足首": "Ankle", "足首D": "AnkleD",
    "足先EX": "ToeEX", "つま先": "Toe",
    "もも": "Thigh",
    "親指": "Thumb", "親指０": "Thumb0", "親指１": "Thumb1",
    "親指２": "Thumb2", "親指先": "ThumbTip",
    "人指": "Index", "人指０": "Index0", "人指１": "Index1",
    "人指２": "Index2", "人指３": "Index3", "人指先": "IndexTip",
    "中指": "Middle", "中指０": "Middle0", "中指１": "Middle1",
    "中指２": "Middle2", "中指３": "Middle3", "中指先": "MiddleTip",
    "薬指": "Ring", "薬指０": "Ring0", "薬指１": "Ring1",
    "薬指２": "Ring2", "薬指３": "Ring3", "薬指先": "RingTip",
    "小指": "Pinky", "小指０": "Pinky0", "小指１": "Pinky1",
    "小指２": "Pinky2", "小指３": "Pinky3", "小指先": "PinkyTip",
    "胸": "Chest", "胸上": "ChestUp", "胸下": "ChestDown",
    "胸下先": "ChestDownTip", "胸先": "ChestTip",
    "おっぱい調整": "BreastAdjust",
    "目": "Eye", "目.L": "Eye.L", "目.R": "Eye.R",
    "両目": "BothEyes", "目先": "EyeFront", "目戻": "EyeReturn",
    "目調整": "EyeAdjust", "目戻.R": "EyeReturn.R", "目戻.L": "EyeReturn.L",
    "舌": "Tongue", "舌先": "TongueTip", "あご": "Jaw", "顎": "Jaw",
    "眉": "Eyebrow", "涙": "Tear", "泣き": "Cry",
    "足ＩＫ": "FootIK", "足IK親": "FootIKParent",
    "つま先ＩＫ": "ToeIK", "足ＩＫ調整": "FootIKAdjust",
    "腰キャンセル": "WaistCancel", "ダミー": "Dummy",
    "調整": "Adjust", "先": "Tip", "非表示": "Hidden",
    "表情": "Expression", "操作中心": "ControlCenter",
    "両目先": "BothEyesFront",
    "頭調整": "HeadAdjust", "首調整": "NeckAdjust",
    "上半身2調整": "UpperBody2Adjust", "上半身調整": "UpperBodyAdjust",
    "下半身調整": "LowerBodyAdjust", "グルーブ調整": "GrooveAdjust",
    "センター調整": "CenterAdjust", "調整ボーン親": "AdjustBoneParent",
    "足調整1": "LegAdjust1", "足調整2": "LegAdjust2",
    "足調整3": "LegAdjust3", "腕調整": "ArmAdjust",
    "肩調整": "ShoulderAdjust", "ひじ調整": "ElbowAdjust",
    "手首調整": "WristAdjust", "腕捩調整": "ArmTwistAdjust",
    "手捩調整": "WristTwistAdjust", "足首調整": "AnkleAdjust",
    "ひざ調整": "KneeAdjust", "足調整": "LegAdjust",
    "肩調整1": "ShoulderAdjust1", "肩調整2": "ShoulderAdjust2",
    "肩調整3": "ShoulderAdjust3",
    "肩調整.R": "ShoulderAdjust.R", "肩調整.L": "ShoulderAdjust.L",
    "肩C調整": "ShoulderCAdjust",
    "上半身2_ＩＫ": "UpperBody2_IK", "上半身3_ウエイト": "UpperBody3_Weight",
    "頭先": "HeadTip", "頭２": "Head2",
    "片": "Side", "片0": "Side0",
    "髪": "Hair", "横髪": "SideHair", "後ろ髪": "BackHair",
    "前髪": "FrontHair", "襟": "Collar", "リボン": "Ribbon",
    "スカート": "Skirt", "フリル": "Frill", "袖": "Sleeve",
    "襟足": "Nape",
    "髪留": "HairPin", "帽子": "Hat", "メガネ": "Glasses",
    "リボン先": "RibbonTip", "リボン先１": "RibbonTip1",
    "リボン先２": "RibbonTip2", "リボン先３": "RibbonTip3",
    "センター先": "CenterTip",
    "腰キャンセル左": "WaistCancelLeft",
    "腰キャンセル右": "WaistCancelRight",
}

# Curated CJK->English morph map: common MMD expression morphs only.
MORPH_MAP = {
    "まばたき": "Blink", "ウィンク": "WinkL", "ウィンク右": "WinkR",
    "笑い": "Smile", "にこり": "Smile2", "なごみ": "SoftEyes",
    "真面目": "Serious", "怒り": "Anger", "困る": "Troubled",
    "びっくり": "Surprise", "じと目": "Glare",
    "あ": "MouthA", "い": "MouthI", "う": "MouthU",
    "え": "MouthE", "お": "MouthO",
    "にやり": "Grin", "口角上げ": "MouthUp", "口角下げ": "MouthDown",
    "頬染め": "Blush",
}

# English base names the model may drive (limbs get .L/.R at digest time).
CONTROL_BONES = {
    "Center", "Waist", "LowerBody", "UpperBody", "UpperBody2",
    "Neck", "Head", "Chest",
    "Shoulder", "Arm", "Elbow", "Wrist",
    "Leg", "Knee", "Ankle", "Toe",
}

_SUFFIX = {".L": ".L", ".R": ".R"}
_PREFIX = {"左": ".L", "右": ".R"}

def translate_bone(cjk: str) -> str:
    """CJK MMD bone name -> English, preserving .L/.R side. Unknown -> unchanged."""
    side = ""
    base = cjk
    for suf, s in _SUFFIX.items():
        if base.endswith(suf):
            side, base = s, base[: -len(suf)]
            break
    else:
        for pre, s in _PREFIX.items():
            if base.startswith(pre):
                side, base = s, base[len(pre):]
                break
    if base in BONE_MAP:
        return BONE_MAP[base] + side
    return cjk
