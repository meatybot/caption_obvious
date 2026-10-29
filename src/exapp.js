/**
 * SPDX-FileCopyrightText: 2026 meatybot
 * SPDX-License-Identifier: MIT
 */

export const PROVIDER_ID = 'caption_obvious_meme'

// AppAPI adds this script with data-base-url, the URL the browser uses to reach the ExApp:
// `/exapps/caption_obvious` with HaRP, the AppAPI PHP proxy otherwise. It also publishes the same URL in
// OCA.AppAPI.referencePickers. currentScript is only set while the entry script runs, so read it now.
export const exAppBaseUrl = document.currentScript?.dataset.baseUrl
	?? window.OCA?.AppAPI?.referencePickers?.[PROVIDER_ID]?.baseUrl
	?? '/exapps/caption_obvious'

export const apiUrl = (path) => `${exAppBaseUrl}/api/${path}`
export const imageUrl = (slug, ext) => `${exAppBaseUrl}/image/${slug}.${ext}`
