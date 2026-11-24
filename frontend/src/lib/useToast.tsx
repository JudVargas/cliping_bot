import { toast } from 'sonner'
import { CheckCircle2, AlertCircle } from 'lucide-react'

export function useToast() {
  return {
    success: (message: string, options?: Parameters<typeof toast.success>[1]) =>
      toast.success(message, options),
    error: (message: string, options?: Parameters<typeof toast.error>[1]) =>
      toast.error(message, options),
    info: (message: string, options?: Parameters<typeof toast.info>[1]) =>
      toast.info(message, options),
    warning: (message: string, options?: Parameters<typeof toast.warning>[1]) =>
      toast.warning(message, options),
    loading: (message: string, options?: Parameters<typeof toast.loading>[1]) =>
      toast.loading(message, options),
    dismiss: (id?: string | number) => toast.dismiss(id),

    /** Toast dedicado para eliminación exitosa de video */
    deleteSuccess: (filename: string) =>
      toast.success('Video eliminado', {
        description: `${filename} y todos sus datos se eliminaron correctamente`,
        icon: <CheckCircle2 size={18} strokeWidth={2} />,
        className: 'toast-delete-success',
      }),

    /** Toast dedicado para error al eliminar video */
    deleteError: (message?: string) =>
      toast.error('Error al eliminar', {
        description: message || 'Intenta de nuevo',
        icon: <AlertCircle size={18} strokeWidth={2} />,
        className: 'toast-delete-error',
        action: {
          label: 'Reintentar',
          onClick: () => {
            window.location.reload()
          },
        },
      }),
  }
}
