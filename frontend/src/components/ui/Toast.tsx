import toast from "react-hot-toast"

export const showToast = {
  success: (message: string) => {
    toast.success(message, {
      className: "border border-emerald-500/20 bg-card text-foreground",
    })
  },
  error: (message: string) => {
    toast.error(message, {
      className: "border border-destructive/20 bg-card text-foreground",
    })
  },
  info: (message: string) => {
    toast(message, {
      className: "border border-blue-500/20 bg-card text-foreground",
    })
  },
}
