# Nano Banana Telegram AI Bot: Deployment and Verification Instructions

This document outlines the necessary steps to redeploy the updated Nano Banana Telegram AI Bot on Railway and verify its core functionalities, including the InstantID face-swapping feature.

## 1. Redeploy on Railway

After the successful push of the latest code to GitHub, you need to trigger a redeployment on Railway. Follow these steps:

1.  **Log in to Railway**: Go to [Railway.app](https://railway.app/) and log in to your account.
2.  **Navigate to your Project**: Select the project corresponding to your Nano Banana bot.
3.  **Trigger Redeploy**: On the project dashboard, locate the deployment section. There should be an option to manually trigger a redeploy. This will pull the latest changes from your GitHub repository and build a new version of your bot.

## 2. Verify Environment Variables

It is crucial to ensure that all necessary environment variables are correctly set in your Railway project. These variables are essential for the bot's functionality.

1.  **Access Variables**: In your Railway project settings, navigate to the "Variables" section.
2.  **Confirm Variables**: Verify that the following environment variables are set with their correct values:
    *   `OPENROUTER_API_KEY`: Your API key for OpenRouter, used for GPT-4o-mini and image generation.
    *   `REPLICATE_API_TOKEN`: Your API token for Replicate, specifically for the InstantID model. (Note: While the `openai_utils.py` was updated to use OpenRouter for image generation, Replicate might still be a fallback or used for specific InstantID calls if not fully migrated. It's safer to keep it configured for now).
    *   `BOT_TOKEN`: Your Telegram Bot API Token, obtained from BotFather.
    *   `ADMIN_ID`: Your Telegram User ID, used for admin functionalities like SBP payment confirmations.

## 3. Test Face Identity (InstantID)

To ensure the InstantID feature is working correctly and provides 100% face similarity, follow these testing steps:

1.  **Start a Chat with the Bot**: Open Telegram and start a chat with your Nano Banana bot.
2.  **Initiate Face Swap**: Send multiple photos (up to 6) of a person whose face you want to swap. The bot should acknowledge each photo received.
3.  **Provide a Prompt**: After sending the photos, send a text prompt describing the desired image (e.g., "a person as a superhero in a futuristic city").
4.  **Verify Output**: The bot should process the request and return an image where the face from your provided photos is accurately swapped onto the generated image, maintaining high similarity.

If any issues arise during these steps, review the bot's logs on Railway for error messages and recheck your environment variable configurations.
