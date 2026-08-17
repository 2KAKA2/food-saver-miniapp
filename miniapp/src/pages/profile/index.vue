<template>
  <view class="page">
    <view class="profile card">
      <view class="avatar">{{ avatarText }}</view>
      <view>
        <text class="nickname">{{ auth.user?.nickname || '微信用户' }}</text>
        <text class="profile-meta">已加入 {{ auth.households.length }} 个家庭</text>
        <text class="edit-profile" @tap="editNickname">修改家庭显示昵称</text>
      </view>
    </view>

    <view class="card section">
      <text class="section-title">当前家庭</text>
      <picker :range="householdNames" :value="householdIndex" @change="switchHousehold">
        <view class="household-picker">
          <view>
            <text class="household-name">{{ auth.currentHousehold?.name || '请选择家庭' }}</text>
            <text class="household-role">{{ auth.currentHousehold?.role === 'owner' ? '家庭所有者' : '家庭成员' }}</text>
          </view>
          <text>切换 ›</text>
        </view>
      </picker>
      <text v-if="isOwner" class="manage-link" @tap="editHouseholdName">修改当前家庭名称</text>
    </view>

    <view class="card section">
      <text class="section-title">家庭成员</text>
      <view v-if="loading" class="empty small">正在加载...</view>
      <ErrorState v-else-if="loadError" :message="loadError" @retry="load" />
      <view v-for="member in loadError ? [] : (detail?.members || [])" :key="member.user.id" class="member-row">
        <view class="member-avatar">{{ member.user.nickname.slice(0, 1) }}</view>
        <view class="member-main">
          <text class="member-name">{{ member.user.nickname }}</text>
          <text class="member-role">{{ member.role === 'owner' ? '所有者' : '成员' }}</text>
        </view>
        <view v-if="isOwner && member.role !== 'owner'" class="member-actions">
          <text class="transfer" @tap="transferOwner(member)">转让</text>
          <text class="remove" @tap="removeMember(member)">移除</text>
        </view>
      </view>
      <button v-if="isOwner" class="secondary-button invite-button" @tap="createInvite">生成家庭邀请码</button>
      <view v-if="inviteCode" class="invite-result" @tap="copyInvite">
        <text class="invite-label">邀请码（点击复制）</text>
        <text class="invite-code">{{ inviteCode }}</text>
        <text class="invite-expiry">24小时内有效，使用一次后失效</text>
        <text class="revoke-invite" @tap.stop="revokeInvite">撤销这个邀请码</text>
      </view>
      <button v-if="!isOwner" class="leave-button" @tap="leaveHousehold">退出当前家庭</button>
    </view>

    <view class="card section">
      <text class="section-title">加入其他家庭</text>
      <view class="inline-form">
        <input v-model="joinCode" class="input" placeholder="粘贴家庭邀请码" />
        <button class="small-button" @tap="joinHousehold">加入</button>
      </view>
    </view>

    <view class="card section">
      <text class="section-title">创建新家庭</text>
      <view class="inline-form">
        <input v-model="newHouseholdName" class="input" placeholder="例如：我们的家" />
        <button class="small-button" @tap="createHousehold">创建</button>
      </view>
    </view>

    <view class="card section legal-list">
      <view class="legal-row" @tap="openLegal('agreement')"><text>用户协议</text><text>›</text></view>
      <view class="legal-row" @tap="openLegal('privacy')"><text>隐私政策</text><text>›</text></view>
      <view class="legal-row danger-row" @tap="deleteAccount"><text>注销账号</text><text>›</text></view>
    </view>

    <button class="logout-button" @tap="logout">退出登录</button>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { api } from '../../api'
import ErrorState from '../../components/ErrorState.vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const detail = ref(null)
const loading = ref(false)
const loadError = ref('')
const inviteCode = ref('')
const inviteId = ref(null)
const joinCode = ref('')
const newHouseholdName = ref('')
const householdNames = computed(() => auth.households.map((item) => `${item.name}（${item.member_count}人）`))
const householdIndex = computed(() => Math.max(0, auth.households.findIndex((item) => item.id === auth.currentHouseholdId)))
const isOwner = computed(() => auth.currentHousehold?.role === 'owner')
const avatarText = computed(() => auth.user?.nickname?.slice(0, 1) || '家')

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    await auth.refresh()
    detail.value = await api.currentHousehold()
  } catch (error) {
    loadError.value = error.message
  } finally {
    loading.value = false
  }
}

async function switchHousehold(event) {
  const household = auth.households[Number(event.detail.value)]
  if (!household) return
  auth.switchHousehold(household.id)
  inviteCode.value = ''
  inviteId.value = null
  await load()
  uni.showToast({ title: `已切换到${household.name}`, icon: 'none' })
}

function editNickname() {
  uni.showModal({
    title: '修改显示昵称',
    content: '该昵称仅用于家庭成员相互识别，不会读取微信昵称。',
    editable: true,
    placeholderText: auth.user?.nickname || '请输入昵称',
    success: async ({ confirm, content }) => {
      const nickname = content?.trim() || ''
      if (!confirm) return
      if (!nickname || nickname.length > 80) {
        uni.showToast({ title: '请输入不超过80个字符的昵称', icon: 'none' })
        return
      }
      try {
        await api.updateProfile({ nickname })
        await load()
        uni.showToast({ title: '昵称已更新' })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none' })
      }
    },
  })
}

function editHouseholdName() {
  uni.showModal({
    title: '修改家庭名称',
    editable: true,
    placeholderText: auth.currentHousehold?.name || '请输入家庭名称',
    success: async ({ confirm, content }) => {
      const name = content?.trim() || ''
      if (!confirm) return
      if (!name || name.length > 80) {
        uni.showToast({ title: '请输入不超过80个字符的家庭名称', icon: 'none' })
        return
      }
      try {
        await api.updateHousehold({ name })
        await load()
        uni.showToast({ title: '家庭名称已更新' })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none' })
      }
    },
  })
}

async function createInvite() {
  try {
    const invite = await api.createInvite({ expires_in_hours: 24, max_uses: 1 })
    inviteId.value = invite.invite_id
    inviteCode.value = invite.invite_code
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  }
}

function copyInvite() {
  uni.setClipboardData({ data: inviteCode.value })
}

async function revokeInvite() {
  if (!inviteId.value) return
  try {
    await api.revokeInvite(inviteId.value)
    inviteId.value = null
    inviteCode.value = ''
    uni.showToast({ title: '邀请码已撤销' })
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  }
}

async function joinHousehold() {
  if (!joinCode.value.trim()) return uni.showToast({ title: '请输入邀请码', icon: 'none' })
  try {
    const household = await api.joinHousehold({ invite_code: joinCode.value.trim() })
    await auth.refresh()
    auth.switchHousehold(household.id)
    joinCode.value = ''
    await load()
    uni.showToast({ title: '已加入家庭' })
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  }
}

async function createHousehold() {
  if (!newHouseholdName.value.trim()) return uni.showToast({ title: '请输入家庭名称', icon: 'none' })
  try {
    const household = await api.createHousehold({ name: newHouseholdName.value.trim() })
    await auth.refresh()
    auth.switchHousehold(household.id)
    newHouseholdName.value = ''
    await load()
    uni.showToast({ title: '家庭创建成功' })
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  }
}

function removeMember(member) {
  uni.showModal({
    title: '移除家庭成员',
    content: `确定将“${member.user.nickname}”移出当前家庭吗？`,
    success: async ({ confirm }) => {
      if (!confirm) return
      try {
        await api.removeMember(member.user.id)
        await auth.refresh()
        await load()
        uni.showToast({ title: '已移除' })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none' })
      }
    },
  })
}

function transferOwner(member) {
  uni.showModal({
    title: '转让家庭所有者',
    content: `转让给“${member.user.nickname}”后，你将变为普通成员，是否继续？`,
    confirmColor: '#b7791f',
    success: async ({ confirm }) => {
      if (!confirm) return
      try {
        await api.transferOwner(member.user.id)
        inviteId.value = null
        inviteCode.value = ''
        await load()
        uni.showToast({ title: '所有者已转让' })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none' })
      }
    },
  })
}

function leaveHousehold() {
  uni.showModal({
    title: '退出当前家庭',
    content: '退出后将无法查看这个家庭的库存、菜谱和消耗记录，是否继续？',
    confirmColor: '#c34249',
    success: async ({ confirm }) => {
      if (!confirm) return
      try {
        await api.leaveHousehold()
        await auth.refresh()
        inviteId.value = null
        inviteCode.value = ''
        await load()
        uni.showToast({ title: '已退出家庭' })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none' })
      }
    },
  })
}

function logout() {
  uni.showModal({
    title: '退出登录',
    content: '确定退出当前账号吗？',
    success: async ({ confirm }) => {
      if (!confirm) return
      await auth.logout()
      uni.reLaunch({ url: '/pages/login/index' })
    },
  })
}

const openLegal = (type) => uni.navigateTo({ url: `/pages/legal/${type}` })

function deleteAccount() {
  uni.showModal({
    title: '注销账号',
    content: '注销后个人资料和个人家庭数据将被删除。若你管理多人家庭，需要先转让所有者。请输入“注销账号”确认：',
    editable: true,
    placeholderText: '注销账号',
    confirmColor: '#c34249',
    success: async ({ confirm, content }) => {
      if (!confirm) return
      try {
        await api.deleteAccount({ confirmation: content })
        auth.clearSession()
        uni.showToast({ title: '账号已注销' })
        setTimeout(() => uni.reLaunch({ url: '/pages/login/index' }), 600)
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3000 })
      }
    },
  })
}

onShow(load)
</script>

<style scoped>
.profile { display: flex; align-items: center; gap: 22rpx; background: linear-gradient(135deg, #2f7d4a, #57a26d); color: #fff; }
.avatar, .member-avatar { display: grid; place-items: center; border-radius: 50%; font-weight: 700; }
.avatar { width: 100rpx; height: 100rpx; background: rgba(255,255,255,.22); font-size: 42rpx; }
.nickname, .profile-meta { display: block; }
.nickname { font-size: 34rpx; font-weight: 700; }
.profile-meta { margin-top: 8rpx; color: rgba(255,255,255,.75); font-size: 23rpx; }
.edit-profile { display: block; margin-top: 12rpx; color: rgba(255,255,255,.9); font-size: 22rpx; text-decoration: underline; }
.section { margin-top: 22rpx; }
.section-title { display: block; margin-bottom: 18rpx; font-size: 30rpx; font-weight: 700; }
.household-picker { display: flex; align-items: center; justify-content: space-between; padding: 16rpx 0; color: #2f7d4a; }
.household-name, .household-role { display: block; }
.household-name { color: #27362c; font-size: 30rpx; font-weight: 650; }
.household-role { margin-top: 6rpx; color: #8a948d; font-size: 22rpx; }
.manage-link { display: block; margin-top: 16rpx; color: #2f7d4a; font-size: 23rpx; }
.member-row { display: flex; align-items: center; padding: 18rpx 0; border-bottom: 1rpx solid #edf0ed; }
.member-avatar { width: 64rpx; height: 64rpx; background: #e7f5eb; color: #2f7d4a; }
.member-main { flex: 1; margin-left: 16rpx; }
.member-name, .member-role { display: block; }
.member-name { font-size: 27rpx; }
.member-role { margin-top: 4rpx; color: #909991; font-size: 21rpx; }
.member-actions { display: flex; gap: 24rpx; font-size: 24rpx; }
.transfer { color: #99701d; }
.remove { color: #c34249; font-size: 24rpx; }
.invite-button { margin-top: 24rpx; }
.invite-result { margin-top: 20rpx; padding: 24rpx; border-radius: 18rpx; background: #f1f7f2; text-align: center; }
.invite-label, .invite-code, .invite-expiry { display: block; }
.invite-label, .invite-expiry { color: #7d8980; font-size: 21rpx; }
.invite-code { margin: 14rpx 0; color: #2f7d4a; font-family: monospace; font-size: 34rpx; font-weight: 700; word-break: break-all; }
.revoke-invite { display: block; margin-top: 18rpx; color: #bd4249; font-size: 23rpx; }
.leave-button { margin-top: 22rpx; background: #fff3f3; color: #bd4249; font-size: 25rpx; }
.inline-form { display: flex; gap: 14rpx; }
.input { flex: 1; height: 74rpx; padding: 0 20rpx; border-radius: 14rpx; background: #f3f6f3; font-size: 25rpx; }
.small-button { width: 130rpx; height: 74rpx; line-height: 74rpx; padding: 0; border-radius: 14rpx; background: #2f7d4a; color: #fff; font-size: 25rpx; }
.logout-button { margin-top: 34rpx; background: transparent; color: #bd4249; font-size: 27rpx; }
.legal-row { display: flex; justify-content: space-between; padding: 22rpx 0; border-bottom: 1rpx solid #edf0ed; font-size: 26rpx; }
.legal-row:last-child { border-bottom: none; }
.danger-row { color: #bd4249; }
.small { padding: 24rpx; }
</style>
