export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const PHONE_PATTERN = /^\+?[0-9\s().-]{7,20}$/;

export function passwordError(password) {
  if (password.length < 8) return "Use at least 8 characters.";
  if (new TextEncoder().encode(password).length > 72) return "Use no more than 72 UTF-8 bytes.";
  if (!/[A-Z]/.test(password)) return "Include at least one uppercase letter.";
  if (!/[a-z]/.test(password)) return "Include at least one lowercase letter.";
  if (!/\d/.test(password)) return "Include at least one number.";
  if (!/[^A-Za-z0-9]/.test(password)) return "Include at least one special character.";
  return "";
}

export function apiError(error) {
  const data = error?.response?.data;
  return {
    message: data?.message || error?.message || "Something went wrong. Please try again.",
    errors: data?.errors
  };
}
