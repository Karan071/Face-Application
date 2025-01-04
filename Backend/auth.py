import logging
import uuid
from functools import wraps
import bcrypt
import jwt
from fastapi import HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from prisma import Prisma
from prisma.models import User




class AuthService:
    """Service for handling authentication."""

    def __init__(
        self, logger: logging.Logger, oauth2_scheme: OAuth2PasswordBearer, db: Prisma
    ):
        """Initialize AuthService."""
        self.logger = logger
        self.oauth2_scheme = oauth2_scheme
        self.db = db
        self.configs = self.read_configs()
        print(f"this is selg config :${self.configs}")

    def read_configs(self):
        """Read configurations from environment variables."""
        return {
            "SECRET_KEY": "your_secret_key",
            "ALGORITHM": "HS256",
        }
        # return read_config_vars(default_configs, ["SECRET_KEY"], self.logger)

    async def generate_token(self, username: str) -> str:
        """Generate a JWT token."""
        try:
            to_encode = {"sub": username, "jti": str(uuid.uuid4())}
            return jwt.encode(
                to_encode,
                self.configs["SECRET_KEY"],
                algorithm=self.configs["ALGORITHM"],
            )
        except jwt.PyJWTError as error:
            err_msg = f"Failed to generate token: {error}"
            self.logger.error(err_msg)
            raise ValueError(err_msg) from error

    async def validate_token(self, token: str) -> bool:
        """Validate the given JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.configs["SECRET_KEY"],
                algorithms=[self.configs["ALGORITHM"]],
            )
            username = payload.get("sub")
            if username is None:
                return False
                
            # Check if user exists and is not disabled
            user = await self.db.user.find_unique(where={"username": username})
            return user is not None and not user.disabled
            
        except jwt.PyJWTError as error:
            self.logger.error("Failed to validate token: %s", error)
            return False

    async def validate_credentials(self, username: str, password: str) -> bool:
        """Validate username and password against stored credentials in database."""
        try:
            user = await self.db.user.find_unique(where={"username": username})
            if user is None:
                return False
            return bcrypt.checkpw(password.encode("utf-8"), user.hashedPassword.encode("utf-8"))
        except Exception as error:
            err_msg = f"Failed to validate credentials: {error}"
            self.logger.error(err_msg)
            raise RuntimeError(err_msg) from error

    async def register_user(self, username: str, email: str, full_name: str, password: str, role: str = "user"):
        """Register a new user with a hashed password."""
        try:
            existing_user = await self.db.user.find_unique(where={"username": username})
            if existing_user:
                self.logger.error("Username already registered: %s", username)
                raise ValueError("Username already registered")

            hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            
            await self.db.user.create(
                data={
                    "username": username,
                    "email": email,
                    "fullName": full_name,
                    "hashedPassword": hashed_password.decode("utf-8"),
                    "role": role
                }
            )
            self.logger.info("Registered new user: %s", username)
        except Exception as error:
            err_msg = f"Failed to register user: {error}"
            self.logger.error(err_msg)
            raise RuntimeError(err_msg) from error

    async def change_password(self, username: str, new_password: str):
        """Change the user's password."""
        try:
            user = await self.db.user.find_unique(where={"username": username})
            if not user:
                self.logger.error("Username does not exist: %s", username)
                raise ValueError("Username does not exist")

            hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
            await self.db.user.update(
                where={"username": username},
                data={"hashedPassword": hashed_password.decode("utf-8")}
            )
            self.logger.info("Password changed for user: %s", username)
        except Exception as error:
            err_msg = f"Failed to change password: {error}"
            self.logger.error(err_msg)
            raise RuntimeError(err_msg) from error