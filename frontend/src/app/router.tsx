import { createBrowserRouter, RouteObject } from 'react-router-dom'
import { Shell } from './Shell'
import { VideosPage } from '../features/videos/VideoList'
import { MomentsPage } from '../features/moments/MomentList'
import { EditorPage } from '../features/editor/ClipEditor'
import { SettingsPage } from '../features/editor/Settings'

const rootLayout: RouteObject = {
  path: '/',
  element: <Shell />,
  children: [
    {
      path: '',
      element: <VideosPage />,
    },
    {
      path: 'videos/:videoId',
      element: <MomentsPage />,
    },
    {
      path: 'clips/:momentId',
      element: <EditorPage />,
    },
    {
      path: 'ajustes',
      element: <SettingsPage />,
    },
  ],
}

export const router = createBrowserRouter([rootLayout])
