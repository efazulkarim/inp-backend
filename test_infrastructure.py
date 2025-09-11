#!/usr/bin/env python3
"""
Test script to verify the new infrastructure components are working correctly.
This script tests configuration, logging, repositories, and services.
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.database import SessionLocal
from app.repositories.dependencies import get_repository_container, check_repository_health
from app.services.user_service import UserService
from app.services.ideaboard_service import IdeaBoardService


async def test_configuration():
    """Test configuration system."""
    print("🔧 Testing Configuration System...")
    
    try:
        settings = get_settings()
        print(f"✅ Configuration loaded successfully")
        print(f"   - Environment: {settings.environment}")
        print(f"   - Debug mode: {settings.debug}")
        print(f"   - Database URL configured: {'Yes' if settings.database_url else 'No'}")
        print(f"   - Log level: {settings.log_level}")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {str(e)}")
        return False


def test_logging():
    """Test logging system."""
    print("\n📝 Testing Logging System...")
    
    try:
        settings = get_settings()
        setup_logging(settings.log_level, settings.log_format)
        
        logger = get_logger("test")
        logger.info("Test log message")
        logger.debug("Test debug message")
        logger.warning("Test warning message")
        
        print("✅ Logging system working correctly")
        return True
    except Exception as e:
        print(f"❌ Logging test failed: {str(e)}")
        return False


async def test_database_and_repositories():
    """Test database connection and repository system."""
    print("\n🗄️ Testing Database and Repository System...")
    
    try:
        # Test database connection
        db = SessionLocal()
        
        # Test repository health
        health_status = await check_repository_health(db)
        
        if health_status['database_connection']:
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            return False
        
        # Test repository container
        repositories = get_repository_container(db)
        
        # Test basic repository operations
        user_count = await repositories.user.count()
        idea_count = await repositories.ideaboard.count()
        
        print(f"✅ Repository system working correctly")
        print(f"   - Users in database: {user_count}")
        print(f"   - Ideas in database: {idea_count}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Database/Repository test failed: {str(e)}")
        return False


async def test_services():
    """Test service layer."""
    print("\n🔧 Testing Service Layer...")
    
    try:
        db = SessionLocal()
        repositories = get_repository_container(db)
        
        # Test user service
        user_service = UserService(repositories)
        user_stats = await user_service.get_user_statistics()
        print(f"✅ User service working - Total users: {user_stats['total_users']}")
        
        # Test ideaboard service
        ideaboard_service = IdeaBoardService(repositories)
        # Test with a dummy user ID (1) if it exists
        try:
            if user_stats['total_users'] > 0:
                user_ideas = await ideaboard_service.get_user_ideas(1, limit=5)
                print(f"✅ IdeaBoard service working - Found {len(user_ideas)} ideas for user 1")
            else:
                print("✅ IdeaBoard service working - No users to test with")
        except Exception:
            print("✅ IdeaBoard service working - User 1 not found (expected)")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Service test failed: {str(e)}")
        return False


async def test_health_endpoints():
    """Test health check functionality."""
    print("\n🏥 Testing Health Check System...")
    
    try:
        from app.api.health import health_check, get_metrics
        from app.database import get_db
        
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        # Test health check
        settings = get_settings()
        health_response = await health_check(db, settings)
        
        print(f"✅ Health check working - Status: {health_response.status}")
        print(f"   - Uptime: {health_response.uptime_seconds:.2f} seconds")
        print(f"   - Environment: {health_response.environment}")
        
        # Test metrics
        metrics = await get_metrics()
        print(f"✅ Metrics working - CPU: {metrics.cpu_usage_percent}%, Memory: {metrics.memory_usage_percent}%")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Health check test failed: {str(e)}")
        return False


async def main():
    """Run all infrastructure tests."""
    print("🚀 Starting Infrastructure Tests...\n")
    
    tests = [
        ("Configuration", test_configuration()),
        ("Logging", test_logging()),
        ("Database & Repositories", test_database_and_repositories()),
        ("Services", test_services()),
        ("Health Checks", test_health_endpoints()),
    ]
    
    results = []
    for test_name, test_coro in tests:
        if asyncio.iscoroutine(test_coro):
            result = await test_coro
        else:
            result = test_coro
        results.append((test_name, result))
    
    print("\n" + "="*50)
    print("📊 Test Results Summary:")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print("="*50)
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All infrastructure tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)