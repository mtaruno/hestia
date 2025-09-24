"""
Firebase Cloud Functions for the Hestia AI Parenting Assistant.

This module contains the cloud functions for the Hestia AI Parenting Assistant:
- get_chat: Handles private chat with the Hestia AI assistant
- auto_respond_post: Automatically responds to community posts
- change_user_id_email: Updates a user's email address
- test_function: A simple test function to verify deployment works
"""
import time
from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore, auth
from firebase_admin.firestore import SERVER_TIMESTAMP
from ai_query.kg_query import run_query
from get_auto_response.get_auto_response import getAutoResponse

# Initialize Firebase app
initialize_app()

@https_fn.on_call()
def get_chat(req: https_fn.Request) -> dict:
    """
    Cloud function to handle private chat with the Hestia AI assistant.

    Args:
        req: The request object containing the query and user ID

    Returns:
        A response containing the generated answer
    """
    # Extract data from request
    query_text = req.data["query"]
    uid = req.data['uid']

    # Get Firestore client
    db = firestore.client()

    # Retrieve recent chat history
    chat_ref = db.collection("chats").document(f"_copilot {uid}").collection("messages")
    messages_query = chat_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10)
    messages = [message.to_dict() for message in messages_query.get()]
    messages.reverse()

    print(f"Chat history: {len(messages)} messages")

    # Generate response using the improved knowledge graph retriever
    response = run_query(query_text)
    print(f"Generated response of length: {len(response)}")

    # Save the response to Firestore
    chat_ref.add({
        "sent_by": "_copilot",
        "content": response,
        "type": "string",
        "timestamp": int(time.time() * 1000)
    })

    return https_fn.Response(response)

@https_fn.on_call()
def auto_respond_post(req: https_fn.Request) -> dict:
    """
    Cloud function to automatically respond to community posts.

    This function uses the knowledge graph to generate a response to a community post
    and saves it as a comment in Firestore.

    Args:
        req: The request object containing the post details

    Returns:
        A response containing the generated answer
    """
    # Extract data from request
    parent_id = req.data["parentID"]
    post_title = req.data["postTitle"]
    post_content = req.data["postContent"]

    # Get Firestore client
    db = firestore.client()

    # Generate response using the improved auto-response function
    response = getAutoResponse(post_title, post_content)
    print(f"Generated auto-response of length: {len(response)}")

    # Save the response to Firestore
    db.collection("comments").document(f"{parent_id}hestia").set({
        "created_at": SERVER_TIMESTAMP,
        "comments": 0,
        "likes": 0,
        "creator": "hestia",
        "parentID": parent_id,
        "comment": response
    })

    return https_fn.Response(response)


@https_fn.on_call()
def change_user_id_email(req: https_fn.CallableRequest) -> dict:
    """
    Cloud function to update a user's email address.

    Args:
        req: The request object containing the new user ID and user ID

    Returns:
        A dictionary indicating success or failure
    """
    try:
        print("Updating user email")
        user_id = req.data.get("newUserID")
        uid = req.data.get("uid")

        if not user_id or not uid:
            return {"success": False, "message": "Missing required parameters"}

        auth.update_user(uid, email=f"{user_id}@tempemail.com")
        print(f"Successfully updated email for user {uid}")
    except ValueError as e:
        print(f"Value error: {str(e)}")
        return {"success": False, "message": str(e)}
    except auth.AuthError as e:
        print(f"Auth error: {str(e)}")
        return {"success": False, "message": str(e)}
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {"success": False, "message": "An unexpected error occurred"}

    return {"success": True, "message": "Email updated successfully"}


@https_fn.on_call()
def test_function(req: https_fn.Request) -> dict:
    """
    A simple test function to verify deployment works.

    Args:
        req: The request object

    Returns:
        A simple response message
    """
    return {"success": True, "message": "Firebase Functions deployment is working!"}
