import { useEffect, useRef } from 'react'
import { WSMessage } from '../types'

const PERMISSION_KEY = 'forexlive_notification_permission_granted'

const requestPermission = async (): Promise<boolean> => {
  if (!('Notification' in window)) return false
  if (Notification.permission === 'granted') return true
  if (Notification.permission === 'denied') return false
  const result = await Notification.requestPermission()
  return result === 'granted'
}

export const useDesktopNotifications = (lastMessage: WSMessage | null) => {
  const permittedRef = useRef(false)

  useEffect(() => {
    if (localStorage.getItem(PERMISSION_KEY) === 'true') {
      permittedRef.current = true
      return
    }
    requestPermission().then((granted) => {
      permittedRef.current = granted
      if (granted) localStorage.setItem(PERMISSION_KEY, 'true')
    })
  }, [])

  useEffect(() => {
    if (!lastMessage || !permittedRef.current) return
    if (document.visibilityState === 'visible') return

    if (lastMessage.type === 'KEY_LEVEL_ALERT' && lastMessage.key_level_triggered) {
      const { level, direction } = lastMessage.key_level_triggered
      const title = `🎯 Key Level Alert — ${lastMessage.pair}`
      const body = `Price touched ${level} (${direction})`
      new Notification(title, { body })
    }

    if (lastMessage.type === 'NEWS_WARNING' && lastMessage.news_warning) {
      const { event, minutes_away, impact } = lastMessage.news_warning
      if (impact === 'HIGH') {
        const title = `⚡ HIGH IMPACT: ${event}`
        const body = `Starts in ${minutes_away} minute${minutes_away === 1 ? '' : 's'}`
        new Notification(title, { body })
      }
    }
  }, [lastMessage])
}
