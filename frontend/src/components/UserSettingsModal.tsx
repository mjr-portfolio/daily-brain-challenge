import { useQuery } from '@tanstack/react-query'
import { useEffect, useState, type FormEvent } from 'react'
import { getAccount, type AccountRead, type ThemePreference } from '@/api/auth.ts'
import { updateMe } from '@/api/users.ts'
import { ModalFrame } from '@/components/ModalFrame.tsx'
import { useAuth } from '@/hooks/useAuth.ts'
import { clearGuestProgress } from '@/utils/storage.ts'

export function UserSettingsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { email, isAuthenticated, updateAccount, deleteAccount } = useAuth()
  const account = useQuery({
    queryKey: ['account'],
    queryFn: getAccount,
    enabled: open && isAuthenticated,
  })
  const [profileEmail, setProfileEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [profilePassword, setProfilePassword] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [deletePassword, setDeletePassword] = useState('')
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  useEffect(() => {
    if (!open || !account.data) return
    setProfileEmail(account.data.email)
    setDisplayName(account.data.display_name ?? '')
  }, [open, account.data])

  if (!open) return null

  function apply(result: AccountRead) {
    updateAccount(result)
  }

  async function run(action: () => Promise<void>) {
    setPending(true)
    setError(null)
    setNotice(null)
    try {
      await action()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update your account')
    } finally {
      setPending(false)
    }
  }

  function onSaveProfile(event: FormEvent) {
    event.preventDefault()
    if (!account.data) return
    const nextEmail = profileEmail.trim().toLowerCase()
    const nextName = displayName.trim()
    const emailChanged = nextEmail !== account.data.email
    const nameChanged = nextName !== (account.data.display_name ?? '')
    if (!emailChanged && !nameChanged) return
    if (emailChanged && !profilePassword) {
      setError('Enter your current password to change your email')
      setNotice(null)
      return
    }
    void run(async () => {
      const result = await updateMe({
        ...(nameChanged ? { display_name: nextName || null } : {}),
        ...(emailChanged ? { email: nextEmail, current_password: profilePassword } : {}),
      })
      apply(result)
      setProfilePassword('')
      setNotice('Account details saved.')
    })
  }

  function onSavePassword(event: FormEvent) {
    event.preventDefault()
    void run(async () => {
      const result = await updateMe({
        current_password: currentPassword,
        new_password: newPassword,
      })
      apply(result)
      setCurrentPassword('')
      setNewPassword('')
      setNotice('Password updated.')
    })
  }

  function onTheme(theme: ThemePreference) {
    if (account.data?.preferences.theme === theme) return
    void run(async () => {
      const result = await updateMe({ theme })
      apply(result)
      setNotice(theme === 'light' ? 'Light theme saved.' : 'Dark theme saved.')
    })
  }

  function onClearGuest() {
    clearGuestProgress()
    setError(null)
    setNotice('Guest data cleared on this browser.')
  }

  function onDelete(event: FormEvent) {
    event.preventDefault()
    void run(async () => {
      await deleteAccount(deletePassword)
      onClose()
    })
  }

  const theme = account.data?.preferences?.theme ?? 'dark'

  return (
    <ModalFrame title="Settings" subtitle={email} onClose={onClose} wide>
      {account.isLoading ? <p className="text-sm text-slate-400">Loading account…</p> : null}
      {error ? <p className="mb-3 text-sm text-rose-300">{error}</p> : null}
      {notice ? <p className="mb-3 text-sm text-emerald-300">{notice}</p> : null}

      <form onSubmit={onSaveProfile}>
        <h3 className="text-sm font-medium text-white">Account details</h3>
        <label className="mt-3 block text-sm text-slate-300" htmlFor="settings-email">
          Email
        </label>
        <input
          id="settings-email"
          type="email"
          required
          value={profileEmail}
          onChange={(event) => setProfileEmail(event.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-amber-400"
        />
        <label className="mt-3 block text-sm text-slate-300" htmlFor="settings-name">
          Display name
        </label>
        <input
          id="settings-name"
          type="text"
          maxLength={32}
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-amber-400"
        />
        <label className="mt-3 block text-sm text-slate-300" htmlFor="settings-profile-password">
          Current password
        </label>
        <input
          id="settings-profile-password"
          type="password"
          autoComplete="current-password"
          value={profilePassword}
          onChange={(event) => setProfilePassword(event.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-amber-400"
        />
        <p className="mt-1 text-xs text-slate-500">Required only when you change your email.</p>
        <div className="mt-3 flex justify-end">
          <SaveButton pending={pending} label="Save details" />
        </div>
      </form>

      <form onSubmit={onSavePassword} className="mt-6 border-t border-slate-800 pt-5">
        <h3 className="text-sm font-medium text-white">Authentication</h3>
        <label className="mt-3 block text-sm text-slate-300" htmlFor="settings-current-password">
          Current password
        </label>
        <input
          id="settings-current-password"
          type="password"
          required
          autoComplete="current-password"
          value={currentPassword}
          onChange={(event) => setCurrentPassword(event.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-amber-400"
        />
        <label className="mt-3 block text-sm text-slate-300" htmlFor="settings-new-password">
          New password
        </label>
        <input
          id="settings-new-password"
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-amber-400"
        />
        <div className="mt-3 flex justify-end">
          <SaveButton pending={pending} label="Update password" />
        </div>
      </form>

      <div className="mt-6 border-t border-slate-800 pt-5">
        <h3 className="text-sm font-medium text-white">Preferences</h3>
        <p className="mt-1 text-xs text-slate-500">Saved on your account for the next time you sign in.</p>
        <div className="mt-3 flex gap-2">
          <ThemeButton selected={theme === 'dark'} onClick={() => onTheme('dark')}>
            Dark
          </ThemeButton>
          <ThemeButton selected={theme === 'light'} onClick={() => onTheme('light')}>
            Light
          </ThemeButton>
        </div>
      </div>

      <div className="mt-6 border-t border-slate-800 pt-5">
        <h3 className="text-sm font-medium text-white">Account actions</h3>
        <button
          type="button"
          onClick={onClearGuest}
          className="mt-3 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:border-amber-400"
        >
          Clear guest data on this browser
        </button>
        <form onSubmit={onDelete} className="mt-4">
          <label className="block text-sm text-slate-300" htmlFor="settings-delete-password">
            Password to delete this account
          </label>
          <input
            id="settings-delete-password"
            type="password"
            required
            autoComplete="current-password"
            value={deletePassword}
            onChange={(event) => setDeletePassword(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-amber-400"
          />
          <button
            type="submit"
            disabled={pending}
            className="mt-3 rounded-lg border border-rose-500 px-3 py-2 text-sm text-rose-200 hover:bg-rose-950 disabled:opacity-60"
          >
            Delete account
          </button>
        </form>
      </div>
    </ModalFrame>
  )
}

function SaveButton({ pending, label }: { pending: boolean; label: string }) {
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-lg border border-amber-500 bg-amber-400 px-3 py-2 text-sm font-medium text-slate-950 hover:border-slate-950 disabled:opacity-60"
    >
      {pending ? 'Saving…' : label}
    </button>
  )
}

function ThemeButton({
  selected,
  onClick,
  children,
}: {
  selected: boolean
  onClick: () => void
  children: string
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-sm ${
        selected
          ? 'bg-amber-400 text-slate-950'
          : 'border border-slate-700 text-slate-300 hover:border-amber-400'
      }`}
    >
      {children}
    </button>
  )
}
