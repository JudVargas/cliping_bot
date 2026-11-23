import { createBrowserRouter, RouteObject } from 'react-router-dom'
import { Shell } from './Shell'
import { VideosPage } from '../features/videos/VideoList'
import { MomentsPage } from '../features/moments/MomentList'
import { EditorPage } from '../features/editor/ClipEditor'
import { SettingsPage } from '../features/editor/Settings'

const rootLayout: RouteObject = {
  path: '/',
  element: React.createElement(Shell),
  children: [
    {
      path: '',
      element: React.createElement(VideosPage),
    },
    {
      path: 'videos/:videoId',
      element: React.createElement(MomentsPage),
    },
    {
      path: 'clips/:momentId',
      element: React.createElement(EditorPage),
    },
    {
      path: 'ajustes',
      element: React.createElement(SettingsPage),
    },
  ],
}

export const router = createBrowserRouter([rootLayout])

import * as React from 'react'
