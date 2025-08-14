import dotenv from "dotenv";

dotenv.config();

export const config = {
  // JWT settings
  JWT_SECRET: process.env.JWT_SECRET || "your-jwt-secret-key",
  JWT_EXPIRES_IN: process.env.JWT_EXPIRES_IN || "1h",
  JWT_REFRESH_SECRET:
    process.env.JWT_REFRESH_SECRET || "your-refresh-secret-key",
  JWT_REFRESH_EXPIRES_IN: process.env.JWT_REFRESH_EXPIRES_IN || "7d",

  // Kakao OAuth settings
  KAKAO_CLIENT_ID: process.env.KAKAO_CLIENT_ID || "",
  KAKAO_CLIENT_SECRET: process.env.KAKAO_CLIENT_SECRET || "",
  KAKAO_REDIRECT_URI:
    process.env.KAKAO_REDIRECT_URI ||
    "http://localhost:3001/auth/kakao/callback",

  // Server settings
  PORT: process.env.PORT || 3000,
  NODE_ENV: process.env.NODE_ENV || "development",

  // Database settings
  DB_USER: process.env.DB_USER || "postgres",
  DB_HOST: process.env.DB_HOST || "localhost",
  DB_NAME: process.env.DB_NAME || "shesawlabs_db",
  DB_PASSWORD: process.env.DB_PASSWORD || "password",
  DB_PORT: parseInt(process.env.DB_PORT || "5432"),

  // Legacy compatibility
  jwt: {
    secret: process.env.JWT_SECRET || "your-jwt-secret-key",
    expiresIn: process.env.JWT_EXPIRES_IN || "1h",
    refreshSecret: process.env.JWT_REFRESH_SECRET || "your-refresh-secret-key",
    refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES_IN || "7d",
  },

  kakao: {
    clientId: process.env.KAKAO_CLIENT_ID || "",
    clientSecret: process.env.KAKAO_CLIENT_SECRET || "",
    redirectUri:
      process.env.KAKAO_REDIRECT_URI ||
      "http://localhost:3001/auth/kakao/callback",
  },
};
