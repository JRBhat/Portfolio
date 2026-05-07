#pip install yt-dlp youtube-transcript-api
import os
import shutil
import urllib.parse
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

def get_video_chapters(video_url):
    """Extracts chapter information from a YouTube video."""
    ydl_opts = {'quiet': True, 'extract_flat': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        return info.get('chapters', [])

def get_transcript(video_id, language="en"):
    """Fetches the transcript of a YouTube video."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
        return transcript
    except Exception as e:
        print(f"Warning: could not fetch transcript: {e}")
        return []

def merge_chapters_transcript(chapters, transcript):
    """Merges transcript into corresponding chapters based on timestamps."""
    markdown_content = "# Video Notes\n\n"

    if not chapters:
        markdown_content += "## Full Transcript\n\n"
        for entry in transcript:
            timestamp = f"{int(entry['start'] // 60)}:{int(entry['start'] % 60):02d}"
            markdown_content += f"- **{timestamp}** {entry['text']}\n"
        markdown_content += "\n"
        return markdown_content

    for i, chapter in enumerate(chapters):
        chapter_title = chapter["title"]
        start_time = chapter["start_time"]
        end_time = chapters[i + 1]["start_time"] if i + 1 < len(chapters) else float("inf")

        markdown_content += f"## {chapter_title}\n\n"
        
        for entry in transcript:
            if start_time <= entry["start"] < end_time:
                timestamp = f"{int(entry['start'] // 60)}:{int(entry['start'] % 60):02d}"
                markdown_content += f"- **{timestamp}** {entry['text']}\n"
        
        markdown_content += "\n"

    return markdown_content

def save_to_markdown(content, filename="youtube_notes.md"):
    """Saves merged transcript and chapters into a Markdown file."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Saved to {filename}")


def main():
    # Input YouTube Video URL
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Replace with your target video URL
    parsed = urllib.parse.urlparse(video_url)
    video_id = urllib.parse.parse_qs(parsed.query).get("v", [None])[0]
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {video_url}")

    # Get Chapters and Transcripts
    chapters = get_video_chapters(video_url)
    transcript = get_transcript(video_id)

    # Merge Data
    markdown_content = merge_chapters_transcript(chapters, transcript)

    # Save to Markdown
    save_to_markdown(markdown_content, "youtube_notes.md")

    # Move to Obsidian Folder (optional — set OBSIDIAN_VAULT_PATH env var)
    obsidian_path = os.environ.get("OBSIDIAN_VAULT_PATH")
    if obsidian_path and os.path.isdir(os.path.dirname(obsidian_path)):
        shutil.move("youtube_notes.md", obsidian_path)
        print(f"Moved to Obsidian: {obsidian_path}")


if __name__ == "__main__":
    main()