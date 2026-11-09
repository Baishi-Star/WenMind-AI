import { createRouter, createWebHistory } from 'vue-router'

import DefaultLayout from '@/layouts/DefaultLayout.vue'
import PortalLayout from '@/layouts/PortalLayout.vue'
import { getRoleHome } from '@/config/portal'
import { useAuthStore } from '@/stores/auth'

const studentRoutes = [
  { path: 'dashboard', name: 'student-dashboard', title: '学生首页', component: () => import('@/views/student/DashboardView.vue') },
  { path: 'tasks', name: 'student-tasks', title: '写作任务', component: () => import('@/views/student/TaskListView.vue') },
  { path: 'essays', name: 'student-essays', title: '我的作文', component: () => import('@/views/student/EssayCenterView.vue') },
  { path: 'essays/new', name: 'student-essay-new', title: '作文提交', component: () => import('@/views/student/EssaySubmitView.vue') },
  { path: 'evaluations', name: 'student-evaluations', title: 'AI 评价结果', component: () => import('@/views/student/EvaluationDetailView.vue') },
  { path: 'revision', name: 'student-revision', title: '修改工作台', component: () => import('@/views/student/RevisionWorkspaceView.vue') },
  { path: 'appeals', name: 'student-appeals', title: '我的申诉', component: () => import('@/views/student/MyAppealsView.vue') },
  { path: 'growth', name: 'student-growth', title: '成长档案', component: () => import('@/views/student/GrowthProfileView.vue') },
  { path: 'training', name: 'student-training', title: '个性化训练', component: () => import('@/views/student/TrainingCenterView.vue') },
]

const teacherRoutes = [
  { path: 'dashboard', name: 'teacher-dashboard', title: '教师工作台', component: () => import('@/views/teacher/DashboardView.vue') },
  { path: 'classes', name: 'teacher-classes', title: '班级管理', component: () => import('@/views/teacher/ClassManagementView.vue') },
  { path: 'assignments', name: 'teacher-assignments', title: '作文任务', component: () => import('@/views/teacher/EssayAssignmentsView.vue') },
  { path: 'reviews', name: 'teacher-reviews', title: '评价复核', component: () => import('@/views/teacher/EvaluationReviewView.vue') },
  { path: 'appeals', name: 'teacher-appeals', title: '申诉管理', component: () => import('@/views/teacher/AppealManagementView.vue') },
  { path: 'analytics', name: 'teacher-analytics', title: '班级学情分析', component: () => import('@/views/teacher/ClassAnalyticsView.vue') },
  { path: 'students/:studentId/growth', name: 'teacher-student-growth', title: '学生成长详情', component: () => import('@/views/teacher/StudentGrowthView.vue') },
  { path: 'disputes', name: 'teacher-disputes', title: '争议分析', component: () => import('@/views/teacher/DisputeAnalysisView.vue') },
  { path: 'rubrics', name: 'teacher-rubrics', title: '规则版本管理', component: () => import('@/views/teacher/RubricManagementView.vue') },
]

const adminRoutes = [
  { path: 'dashboard', name: 'admin-dashboard', title: '系统概览', component: () => import('@/views/admin/DashboardView.vue') },
  { path: 'knowledge', name: 'admin-knowledge', title: '知识库管理', component: () => import('@/views/admin/KnowledgeBaseView.vue') },
  { path: 'agents', name: 'admin-agents', title: 'Agent 运行监控', component: () => import('@/views/admin/AgentMonitorView.vue') },
  { path: 'model', name: 'admin-model', title: '模型配置', component: () => import('@/views/admin/ModelConfigView.vue') },
  { path: 'prompts', name: 'admin-prompts', title: 'Prompt 管理', component: () => import('@/views/admin/PromptManagementView.vue') },
  { path: 'logs', name: 'admin-logs', title: '系统运行日志', component: () => import('@/views/admin/SystemLogsView.vue') },
]

function buildPortalRoutes(role, children) {
  return {
    path: `/${role}`,
    component: PortalLayout,
    meta: { roles: [role] },
    children: children.map((route) => ({
      ...route,
      meta: { title: route.title, roles: [role], role },
    })),
  }
}

const routes = [
  {
    path: '/',
    component: DefaultLayout,
    children: [
      {
        path: '',
        name: 'home',
        component: () => import('@/views/HomeView.vue'),
        meta: { title: '首页', public: true },
      },
      {
        path: 'system/status',
        name: 'system-status',
        component: () => import('@/views/SystemStatusView.vue'),
        meta: { title: '后端连接测试', public: true },
      },
    ],
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { title: '演示角色登录', public: true },
  },
  buildPortalRoutes('student', studentRoutes),
  buildPortalRoutes('teacher', teacherRoutes),
  buildPortalRoutes('admin', adminRoutes),
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在', public: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const authStore = useAuthStore()
  if (to.meta.public) {
    return true
  }
  if (!authStore.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  const allowedRoles = to.meta.roles || []
  if (allowedRoles.length > 0 && !allowedRoles.includes(authStore.role)) {
    return getRoleHome(authStore.role)
  }
  return true
})

router.afterEach((to) => {
  const baseTitle = import.meta.env.VITE_APP_TITLE || 'WenMind AI 文思智评'
  document.title = to.meta.title ? `${to.meta.title} · ${baseTitle}` : baseTitle
})

export default router