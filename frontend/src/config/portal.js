import {
  ChatLineSquare,
  Collection,
  Connection,
  DataAnalysis,
  DocumentChecked,
  Files,
  FolderOpened,
  Histogram,
  Monitor,
  Odometer,
  Search,
  TrendCharts,
} from '@element-plus/icons-vue'

export const ROLES = {
  student: {
    key: 'student',
    name: '学生',
    englishName: 'Student',
    homePath: '/student/dashboard',
    demoName: '演示学生',
    description: '提交作文、查看 AI 诊断与原文证据、提出申诉、跟踪个人写作成长。',
    highlights: ['多维评价与证据追溯', '申诉进度可查', '成长画像与专项训练'],
  },
  teacher: {
    key: 'teacher',
    name: '教师',
    englishName: 'Teacher',
    homePath: '/teacher/dashboard',
    demoName: '演示教师',
    description: '管理班级与作文任务，复核学生申诉，基于真实评价记录开展学情分析。',
    highlights: ['AI 初评与人工复核对照', '班级共性问题识别', '评价规则版本审核'],
  },
  admin: {
    key: 'admin',
    name: '管理员',
    englishName: 'Admin',
    homePath: '/admin/dashboard',
    demoName: '演示管理员',
    description: '维护写作知识库、Agent 运行监控、模型与 Prompt 配置及系统运行状态。',
    highlights: ['知识库解析与检索测试', 'Agent 真实运行日志', '模型与 Prompt 版本管理'],
  },
}

export const NAVIGATIONS = {
  student: [
    { path: '/student/dashboard', title: '学生首页', icon: Odometer, group: '学习概览' },
    { path: '/student/essays', title: '我的作文', icon: Files, group: '写作与评价' },
    { path: '/student/evaluations', title: 'AI 评价结果', icon: DocumentChecked, group: '写作与评价' },
    { path: '/student/appeals', title: '我的申诉', icon: ChatLineSquare, group: '反馈与成长' },
    { path: '/student/growth', title: '成长档案', icon: TrendCharts, group: '反馈与成长' },
  ],
  teacher: [
    { path: '/teacher/dashboard', title: '教师工作台', icon: Odometer, group: '教学概览' },
    { path: '/teacher/reviews', title: '评价复核', icon: DocumentChecked, group: '评价与复核' },
    { path: '/teacher/appeals', title: '申诉管理', icon: ChatLineSquare, group: '评价与复核' },
    { path: '/teacher/analytics', title: '班级学情分析', icon: Histogram, group: '分析与改进' },
    { path: '/teacher/disputes', title: '争议分析', icon: DataAnalysis, group: '分析与改进' },
    { path: '/teacher/rubrics', title: '规则版本管理', icon: Collection, group: '分析与改进' },
  ],
  admin: [
    { path: '/admin/dashboard', title: '系统概览', icon: Monitor, group: '运行中心' },
    { path: '/admin/knowledge', title: '知识库管理', icon: FolderOpened, group: '知识与模型' },
    { path: '/admin/agents', title: 'Agent 运行监控', icon: Connection, group: '知识与模型' },
  ],
}

export function getRoleHome(role) {
  return ROLES[role]?.homePath || '/login'
}

export function getRoleLabel(role) {
  return ROLES[role]?.name || '未登录'
}

export function findNavigation(role, path) {
  return (NAVIGATIONS[role] || []).find((item) => item.path === path)
}

export const SEARCH_ICON = Search