"""幂等演示数据：所有账号、班级、题目和作文均以 is_demo 明确标注。"""
import json
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.base import EssayStatus, UserRole
from app.models.essay import Essay, EssayPrompt
from app.models.rubric import RubricVersion
from app.models.user import ClassRoom, Enrollment, User

logger = get_logger(__name__)


def _demo_password() -> str:
    configured = settings.demo_password.strip()
    if configured:
        return configured
    generated = secrets.token_urlsafe(12)
    logger.warning("未配置 DEMO_PASSWORD，已生成本次演示密码：%s（仅首次初始化有效，请记录并自行修改）", generated)
    return generated

ESSAY_CONTENTS = [
    "信息每天都在涌来，真正稀缺的却不是消息，而是判断消息的能力。面对热搜与短视频，我们常常在不知不觉中被情绪推着前进，把别人的结论当作自己的思考。独立思考首先意味着愿意停顿：这条信息的来源可靠吗，它省略了哪些背景，我是否只因为观点符合预期就选择相信？\n其次，独立思考不等于拒绝一切他人意见。相反，它需要主动接触不同立场，在比较中修正自己的判断。若只把与自己相同的声音留在耳边，所谓坚持自我便可能只是另一种盲从。\n因此，我们既要保持求证的耐心，也要保留被事实说服的勇气。信息洪流无法阻挡，但一个人可以决定自己站在哪里。让判断慢一点，让证据多一步，我们才有可能在喧闹中守住清醒。",
    "技术的发展不断拓展人的能力，也重新提醒我们思考人的位置。当算法可以生成文章、安排路线甚至替人作出选择时，便利确实增加了，但便利并不天然等于进步。如果所有决定都交给系统，人可能在轻松中逐渐失去理解世界和承担责任的机会。\n当然，拒绝技术并不是答案。真正重要的是明确工具的边界：让机器处理重复劳动，让人保留价值判断；让数据提供参考，让最终决定能够被人解释。技术的意义应当是让人的创造更有空间，而不是让人变成流程中被动的一环。\n面对未来，我们需要的不是对机器的盲目崇拜，也不是无端恐惧，而是清醒的主体意识。只有知道为什么使用技术、准备用它实现什么，技术才会成为延伸能力的工具，而不是替代思考的理由。",
    "成长常被理解为不断获得正确答案，但真正的成长也往往包含承认不确定。一次作文评价给出的分数，可以帮助我们发现问题，却不能概括一个写作者的全部可能。如果只因分数不理想便否定自己，评价就从诊断工具变成了束缚。\n更有价值的做法，是追问评价背后的依据：观点是否清晰，论据是否真正支撑观点，段落之间是否形成递进。把抽象分数转化为具体行动，我们才知道下一次应该修改什么。\n同时，评价也需要被质疑。读者可能误解作者的表达，标准也可能忽略有个性的写法。提出异议并说明理由，不是拒绝批评，而是参与对作品的理解。写作因此不再只是等待判定，而成为作者、读者与标准之间持续对话的过程。",
]


def seed_demo_data(db: Session) -> bool:
    if db.scalar(select(User.id).limit(1)) is not None:
        logger.info("检测到已有用户数据，跳过演示数据初始化")
        return False

    seed_value = _demo_password()
    users = [
        User(username="demo_student", password_hash=hash_password(seed_value), display_name="演示学生一", role=UserRole.STUDENT, is_demo=True),
        User(username="demo_student2", password_hash=hash_password(seed_value), display_name="演示学生二", role=UserRole.STUDENT, is_demo=True),
        User(username="demo_student3", password_hash=hash_password(seed_value), display_name="演示学生三", role=UserRole.STUDENT, is_demo=True),
        User(username="demo_teacher", password_hash=hash_password(seed_value), display_name="演示教师", role=UserRole.TEACHER, is_demo=True),
        User(username="demo_admin", password_hash=hash_password(seed_value), display_name="演示管理员", role=UserRole.ADMIN, is_demo=True),
    ]
    db.add_all(users)
    db.flush()
    students = users[:3]
    teacher = users[3]
    admin = users[4]

    classroom = ClassRoom(name="高一（1）班（演示）", teacher_id=teacher.id, is_demo=True)
    db.add(classroom)
    db.flush()
    db.add_all([Enrollment(class_id=classroom.id, student_id=student.id) for student in students])

    dimensions = [
        {"dimension": "content", "name": "内容", "max_score": 20, "description": "审题切题、立意、观点、论据与分析"},
        {"dimension": "organization", "name": "组织", "max_score": 20, "description": "段落功能、论证顺序、逻辑连贯与衔接"},
        {"dimension": "language", "name": "语言", "max_score": 20, "description": "表达准确、流畅、句式与语言规范"},
    ]
    rubric = RubricVersion(
        name="高中议论文诊断性评价量规（演示）",
        version="v1.0",
        dimensions_json=json.dumps({"total_max_score": 60, "dimensions": dimensions}, ensure_ascii=False),
        status="published",
        change_reason="初赛演示初始量规；仅用于教学诊断，不等同于高考正式阅卷标准",
        is_demo=True,
        created_by=admin.id,
    )
    db.add(rubric)
    db.flush()

    prompts = [
        EssayPrompt(title="在信息洪流中保持独立思考（演示）", requirements="围绕信息时代的独立思考写一篇议论文，观点明确，论据恰当，不少于 600 字。", rubric_version_id=rubric.id, is_demo=True, created_by=teacher.id),
        EssayPrompt(title="科技发展与人的主体性（演示）", requirements="结合现实谈谈技术发展应如何服务人的成长，写一篇议论文，不少于 600 字。", rubric_version_id=rubric.id, is_demo=True, created_by=teacher.id),
        EssayPrompt(title="如何面对成长中的评价（演示）", requirements="结合学习经历，论述如何理性看待评价与质疑，做到观点清晰、结构完整。", rubric_version_id=rubric.id, is_demo=True, created_by=teacher.id),
    ]
    db.add_all(prompts)
    db.flush()

    essays = [
        Essay(
            student_id=student.id,
            prompt_id=prompt.id,
            content=content,
            content_version=1,
            char_count=len(content),
            status=EssayStatus.SUBMITTED,
            is_demo=True,
        )
        for student, prompt, content in zip(students, prompts, ESSAY_CONTENTS, strict=True)
    ]
    db.add_all(essays)
    db.commit()
    logger.info("演示数据初始化完成：5 个账号、1 个班级、1 份量规、3 个题目、3 篇作文")
    return True