"""
Tests for Mergington High School Activities API

Tests cover all main endpoints with happy path, error cases, and edge cases.
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Provide a test client for the FastAPI application."""
    return TestClient(app)


class TestGetActivities:
    """Tests for GET /activities endpoint."""

    def test_get_activities_success(self, client):
        """Test successfully retrieving all activities."""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response is a dictionary with activities
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Verify activity structure
        for activity_name, activity_data in data.items():
            assert isinstance(activity_name, str)
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_get_activities_contains_known_activities(self, client):
        """Test that response includes expected activities."""
        response = client.get("/activities")
        data = response.json()
        
        expected_activities = ["Chess Club", "Programming Class", "Gym Class"]
        for activity in expected_activities:
            assert activity in data


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint."""

    def test_signup_success(self, client):
        """Test successfully signing up for an activity."""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "new.student@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "new.student@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]

    def test_signup_adds_participant(self, client):
        """Test that signup actually adds the participant to the activity."""
        email = "test.signup@mergington.edu"
        
        # Sign up
        response = client.post(
            "/activities/Art Club/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify participant is in the activity
        activities = client.get("/activities").json()
        assert email in activities["Art Club"]["participants"]

    def test_signup_duplicate_email(self, client):
        """Test that duplicate signup is rejected."""
        email = "duplicate@mergington.edu"
        activity = "Drama Club"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second signup with same email should fail
        response2 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"].lower()

    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity."""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_multiple_different_activities(self, client):
        """Test same student can signup for multiple different activities."""
        email = "multi.student@mergington.edu"
        
        # Sign up for first activity
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Sign up for second activity
        response2 = client.post(
            "/activities/Basketball Team/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify both signups worked
        activities = client.get("/activities").json()
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Basketball Team"]["participants"]


class TestUnregisterFromActivity:
    """Tests for POST /activities/{activity_name}/unregister endpoint."""

    def test_unregister_success(self, client):
        """Test successfully unregistering from an activity."""
        email = "unreg.test@mergington.edu"
        activity = "Soccer Club"
        
        # First sign up
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Then unregister
        response = client.post(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]

    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes the participant."""
        email = "removal.test@mergington.edu"
        activity = "Debate Club"
        
        # Sign up
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Verify participant is added
        activities_before = client.get("/activities").json()
        assert email in activities_before[activity]["participants"]
        
        # Unregister
        client.post(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        # Verify participant is removed
        activities_after = client.get("/activities").json()
        assert email not in activities_after[activity]["participants"]

    def test_unregister_not_signed_up(self, client):
        """Test unregister for someone not signed up."""
        response = client.post(
            "/activities/Science Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"].lower()

    def test_unregister_activity_not_found(self, client):
        """Test unregister from non-existent activity."""
        response = client.post(
            "/activities/Fake Activity/unregister",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_unregister_and_signup_again(self, client):
        """Test that a student can re-signup after unregistering."""
        email = "resignup.test@mergington.edu"
        activity = "Programming Class"
        
        # Sign up
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Unregister
        client.post(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        # Sign up again
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_signup_to_activity_with_existing_participants(self, client):
        """Test signup to activity that already has participants."""
        activities = client.get("/activities").json()
        
        # Find an activity with existing participants
        activity_with_participants = None
        for name, data in activities.items():
            if len(data["participants"]) > 0:
                activity_with_participants = name
                break
        
        if activity_with_participants:
            initial_count = len(activities[activity_with_participants]["participants"])
            
            # Add new participant
            response = client.post(
                f"/activities/{activity_with_participants}/signup",
                params={"email": "edge.case@mergington.edu"}
            )
            assert response.status_code == 200
            
            # Verify all existing participants are still there
            activities_after = client.get("/activities").json()
            assert len(activities_after[activity_with_participants]["participants"]) == initial_count + 1

    def test_activity_capacity_tracking(self, client):
        """Test that available spots are tracked correctly."""
        activities = client.get("/activities").json()
        activity_name = "Gym Class"
        activity = activities[activity_name]
        
        max_spots = activity["max_participants"]
        current_participants = len(activity["participants"])
        expected_spots_left = max_spots - current_participants
        
        # Verify the availability calculation works
        assert expected_spots_left >= 0
        
        # Try to fill remaining spots
        for i in range(min(2, expected_spots_left)):  # Just test a couple
            email = f"capacity.test.{i}@mergington.edu"
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200

    def test_email_with_special_characters(self, client):
        """Test signup with email containing special characters."""
        email = "student+tag@mergington.edu"
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        activities = client.get("/activities").json()
        assert email in activities["Chess Club"]["participants"]
