from uuid import UUID

class User:
    id: UUID = UUID('00000000-0000-0000-0000-000000000001')

# Dependency placeholder for current user (replace with actual auth dependency)
async def get_current_user():
    return User()
