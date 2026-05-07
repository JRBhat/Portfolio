"""
Job Skills Tracker - Interactive Word Cloud Application
Extracts tech skills from job descriptions and visualizes them
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import webbrowser
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class JobSkillsTracker:
    def __init__(self, data_file: str = "job_skills_data.json"):
        self.data_file = Path(data_file)
        self.skills_data = self.load_data()

        self.job_title_keywords = {
            'data scientist', 'senior data scientist', 'lead data scientist', 'staff data scientist',
            'data analyst', 'senior data analyst', 'business analyst', 'analytics engineer',
            'data engineer', 'senior data engineer', 'lead data engineer', 'staff data engineer',
            'machine learning engineer', 'ml engineer', 'senior ml engineer', 'mlops engineer',
            'ai engineer', 'ai researcher', 'research scientist', 'applied scientist',
            'software engineer', 'senior software engineer', 'staff software engineer',
            'backend engineer', 'frontend engineer', 'full stack engineer', 'fullstack developer',
            'devops engineer', 'site reliability engineer', 'sre', 'platform engineer',
            'solutions architect', 'software architect', 'principal engineer',
            'engineering manager', 'technical lead', 'tech lead', 'team lead',
            'product manager', 'technical product manager', 'data product manager',
            'quantitative analyst', 'quantitative researcher', 'quant',
            'business intelligence analyst', 'bi analyst', 'bi developer',
            'data science manager', 'analytics manager', 'head of data',
            'python developer', 'java developer', 'javascript developer',
            'deep learning engineer', 'nlp engineer', 'computer vision engineer',
            'cloud engineer', 'cloud architect', 'solutions engineer',
        }

        self.tech_skills = {
            # Programming Languages
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'go', 'rust',
            'scala', 'kotlin', 'swift', 'r', 'matlab', 'julia', 'perl', 'php', 'bash', 'shell',
            # Data Science & ML
            'machine learning', 'deep learning', 'neural networks', 'nlp', 'computer vision',
            'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'sklearn', 'pandas', 'numpy',
            'scipy', 'matplotlib', 'seaborn', 'plotly', 'tableau', 'power bi', 'looker',
            'xgboost', 'lightgbm', 'catboost', 'hugging face', 'transformers', 'bert', 'gpt',
            'llm', 'large language models', 'generative ai', 'rag', 'langchain',
            # Databases
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'cassandra', 'dynamodb',
            'oracle', 'sql server', 'sqlite', 'elasticsearch', 'neo4j', 'snowflake',
            'bigquery', 'redshift', 'databricks',
            # Cloud & DevOps
            'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'jenkins',
            'terraform', 'ansible', 'ci/cd', 'gitlab', 'github actions', 'circleci',
            'cloudformation', 'lambda', 's3', 'ec2', 'ecs', 'eks',
            # Web Development
            'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask', 'fastapi',
            'spring', 'spring boot', 'html', 'css', 'sass', 'webpack', 'next.js', 'nest.js',
            'graphql', 'rest api', 'microservices',
            # Big Data
            'spark', 'hadoop', 'kafka', 'airflow', 'flink', 'hive', 'pig', 'presto',
            'dbt', 'etl', 'data pipelines', 'data engineering',
            # Version Control & Tools
            'git', 'github', 'gitlab', 'bitbucket', 'svn', 'jira', 'confluence',
            # Testing
            'pytest', 'junit', 'selenium', 'cypress', 'jest', 'unit testing', 'integration testing',
            # Other
            'agile', 'scrum', 'api', 'linux', 'unix', 'statistics', 'optimization',
            'algorithms', 'data structures', 'oop', 'functional programming',
            'reinforcement learning', 'time series', 'a/b testing', 'experimentation',
        }

    @staticmethod
    def _default_data() -> Dict:
        return {"skills": {}, "job_titles": {}, "jobs": []}

    def load_data(self) -> Dict:
        """Load existing data from JSON file"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                for key, default in self._default_data().items():
                    data.setdefault(key, default)
                return data
            except json.JSONDecodeError:
                pass
        return self._default_data()

    def save_data(self):
        """Save data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.skills_data, f, indent=2)

    def extract_skills(self, text: str) -> Set[str]:
        """Extract tech skills from job description text"""
        text_lower = text.lower()
        return {
            skill for skill in self.tech_skills
            if re.search(r'\b' + re.escape(skill) + r'\b', text_lower)
        }

    def extract_job_title(self, text: str) -> str:
        """Extract job title from job description text"""
        text_lower = text.lower()

        title_match = re.search(r'(?:job\s+)?title\s*[:：]\s*([^\n\r]+)', text_lower)
        if title_match:
            potential_title = title_match.group(1).strip()
            for keyword in self.job_title_keywords:
                if keyword in potential_title:
                    return keyword.title()

        first_text = ' '.join(text_lower.split('\n')[:3])
        best_from_header = max(
            (kw for kw in self.job_title_keywords if kw in first_text),
            key=len,
            default=None,
        )
        if best_from_header:
            return best_from_header.title()

        for keyword in sorted(self.job_title_keywords, key=len, reverse=True):
            if keyword in text_lower:
                return keyword.title()

        return "Unspecified Role"

    def _update_skills_index(self, job_id: int, skills: Set[str], job_title: str):
        """Update the skills index with data from one job"""
        for skill in skills:
            entry = self.skills_data["skills"].setdefault(skill, {
                "count": 0, "job_ids": [], "job_titles": {}
            })
            entry["count"] += 1
            entry["job_ids"].append(job_id)
            entry["job_titles"][job_title] = entry["job_titles"].get(job_title, 0) + 1

    def _update_titles_index(self, job_id: int, job_title: str, skills: Set[str]):
        """Update the job titles index with data from one job"""
        entry = self.skills_data["job_titles"].setdefault(job_title, {
            "count": 0, "job_ids": [], "skills": {}
        })
        entry["count"] += 1
        entry["job_ids"].append(job_id)
        for skill in skills:
            entry["skills"][skill] = entry["skills"].get(skill, 0) + 1

    def add_job_description(self, job_text: str, job_url: str) -> Dict:
        """Add a new job description and update skill and job title indices"""
        skills = self.extract_skills(job_text)
        job_title = self.extract_job_title(job_text)
        job_id = len(self.skills_data["jobs"])

        self.skills_data["jobs"].append({
            "id": job_id,
            "url": job_url,
            "title": job_title,
            "skills": list(skills),
        })

        if skills:
            self._update_skills_index(job_id, skills, job_title)
            self._update_titles_index(job_id, job_title, skills)

        self.save_data()
        return {
            "skills": {s: self.skills_data["skills"][s]["count"] for s in skills},
            "job_title": job_title,
        }

    def get_skills_frequencies(self) -> Dict[str, int]:
        """Get all skills with their frequencies"""
        return {skill: data["count"] for skill, data in self.skills_data["skills"].items()}

    def get_job_title_frequencies(self) -> Dict[str, int]:
        """Get all job titles with their frequencies"""
        return {title: data["count"] for title, data in self.skills_data["job_titles"].items()}

    def _get_jobs_by_ids(self, job_ids: List[int]) -> List[Dict]:
        jobs = self.skills_data["jobs"]
        return [jobs[jid] for jid in job_ids if jid < len(jobs)]

    def get_jobs_for_skill(self, skill: str) -> List[Dict]:
        """Get all job details that mention a specific skill"""
        if skill not in self.skills_data["skills"]:
            return []
        return [
            {"url": j["url"], "title": j.get("title", "Unspecified Role")}
            for j in self._get_jobs_by_ids(self.skills_data["skills"][skill]["job_ids"])
        ]

    def get_jobs_for_title(self, job_title: str) -> List[Dict]:
        """Get all job details for a specific job title"""
        if job_title not in self.skills_data["job_titles"]:
            return []
        return [
            {"url": j["url"], "skills": j.get("skills", [])}
            for j in self._get_jobs_by_ids(self.skills_data["job_titles"][job_title]["job_ids"])
        ]

    def get_skills_for_job_title(self, job_title: str) -> Dict[str, int]:
        """Get skills associated with a specific job title and their frequencies"""
        return self.skills_data["job_titles"].get(job_title, {}).get("skills", {})

    def get_job_titles_for_skill(self, skill: str) -> Dict[str, int]:
        """Get job titles associated with a specific skill and their frequencies"""
        return self.skills_data["skills"].get(skill, {}).get("job_titles", {})

    def get_counts(self) -> Dict[str, int]:
        """Return aggregate counts for display"""
        return {
            "jobs": len(self.skills_data["jobs"]),
            "skills": len(self.skills_data["skills"]),
            "job_titles": len(self.skills_data["job_titles"]),
        }

    def clear_all_data(self):
        """Clear all stored data"""
        self.skills_data = self._default_data()
        self.save_data()


class JobSkillsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Job Skills Tracker - Interactive Word Cloud")
        self.root.geometry("1200x900")

        self.tracker = JobSkillsTracker()

        self.create_input_frame()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.skills_tab = ttk.Frame(self.notebook)
        self.titles_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.skills_tab, text="Skills Word Cloud")
        self.notebook.add(self.titles_tab, text="Job Titles Word Cloud")

        self.create_skills_visualization_frame()
        self.create_titles_visualization_frame()
        self.create_stats_frame()

        self.update_skills_wordcloud()
        self.update_titles_wordcloud()

    def create_input_frame(self):
        """Create the input section"""
        input_frame = ttk.LabelFrame(self.root, text="Add Job Description", padding=10)
        input_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)

        url_frame = ttk.Frame(input_frame)
        url_frame.pack(fill=tk.X, pady=5)
        ttk.Label(url_frame, text="Job URL:").pack(side=tk.LEFT, padx=5)
        self.url_entry = ttk.Entry(url_frame, width=80)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Label(input_frame, text="Job Description:").pack(anchor=tk.W, pady=5)
        self.job_text = scrolledtext.ScrolledText(input_frame, height=8, wrap=tk.WORD)
        self.job_text.pack(fill=tk.BOTH, expand=True, pady=5)

        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="Add Job Description", command=self.add_job).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Input", command=self.clear_input).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear All Data", command=self.clear_all_data).pack(side=tk.LEFT, padx=5)

    def create_skills_visualization_frame(self):
        """Create the skills word cloud visualization section"""
        viz_frame = ttk.Frame(self.skills_tab, padding=10)
        viz_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(viz_frame, text="Click on skills to see jobs and related titles",
                  font=('Arial', 10)).pack(pady=5)
        self.skills_fig, self.skills_ax = plt.subplots(figsize=(10, 6))
        self.skills_canvas = FigureCanvasTkAgg(self.skills_fig, master=viz_frame)
        self.skills_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.skills_canvas.mpl_connect('button_press_event', self.on_skills_wordcloud_click)

    def create_titles_visualization_frame(self):
        """Create the job titles word cloud visualization section"""
        viz_frame = ttk.Frame(self.titles_tab, padding=10)
        viz_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(viz_frame, text="Click on job titles to see related jobs and skills",
                  font=('Arial', 10)).pack(pady=5)
        self.titles_fig, self.titles_ax = plt.subplots(figsize=(10, 6))
        self.titles_canvas = FigureCanvasTkAgg(self.titles_fig, master=viz_frame)
        self.titles_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.titles_canvas.mpl_connect('button_press_event', self.on_titles_wordcloud_click)

    def create_stats_frame(self):
        """Create statistics display section"""
        stats_frame = ttk.LabelFrame(self.root, text="Statistics", padding=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        self.stats_label = ttk.Label(stats_frame,
                                     text="Total Jobs: 0 | Unique Skills: 0 | Unique Job Titles: 0")
        self.stats_label.pack()

    def _generate_wordcloud(self, ax, canvas, frequencies: Dict, title: str,
                            colormap: str, storage_attr: str):
        """Render a word cloud onto the given axes; store the WordCloud object for click detection"""
        ax.clear()
        if not frequencies:
            ax.text(0.5, 0.5, 'No data yet!\n\nAdd job descriptions to see the word cloud',
                    ha='center', va='center', fontsize=14, color='gray')
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            canvas.draw()
            self.update_stats()
            return

        wc = WordCloud(
            width=1000, height=600,
            background_color='white',
            colormap=colormap,
            relative_scaling=0.5,
            min_font_size=10,
        ).generate_from_frequencies(frequencies)

        ax.imshow(wc, interpolation='bilinear')
        ax.axis('off')
        ax.set_title(title, fontsize=12, pad=20)
        setattr(self, storage_attr, wc)
        canvas.draw()
        self.update_stats()

    @staticmethod
    def _find_clicked_word(x: int, y: int, layout) -> Optional[str]:
        """Return the word at pixel coordinates (x, y) in a word cloud layout, or None"""
        for (word, _count), font_size, position, _orientation, _color in layout:
            word_x, word_y = position
            if (word_x <= x <= word_x + len(word) * font_size * 0.6
                    and word_y - font_size <= y <= word_y):
                return word
        return None

    def update_skills_wordcloud(self):
        """Refresh the skills word cloud"""
        self._generate_wordcloud(
            self.skills_ax, self.skills_canvas,
            self.tracker.get_skills_frequencies(),
            'Tech Skills - Click to see jobs and related titles',
            'viridis',
            'current_skills_wordcloud',
        )

    def update_titles_wordcloud(self):
        """Refresh the job titles word cloud"""
        self._generate_wordcloud(
            self.titles_ax, self.titles_canvas,
            self.tracker.get_job_title_frequencies(),
            'Job Titles - Click to see jobs and required skills',
            'plasma',
            'current_titles_wordcloud',
        )

    def update_stats(self):
        """Update statistics display"""
        counts = self.tracker.get_counts()
        self.stats_label.config(
            text=f"Total Jobs: {counts['jobs']} | "
                 f"Unique Skills: {counts['skills']} | "
                 f"Unique Job Titles: {counts['job_titles']}"
        )

    def on_skills_wordcloud_click(self, event):
        """Handle clicks on the skills word cloud"""
        if event.inaxes != self.skills_ax or not hasattr(self, 'current_skills_wordcloud'):
            return
        try:
            word = self._find_clicked_word(
                int(event.xdata), int(event.ydata),
                self.current_skills_wordcloud.layout_,
            )
            if word:
                self.show_skill_details(word)
        except Exception as e:
            print(f"Error detecting clicked word: {e}")

    def on_titles_wordcloud_click(self, event):
        """Handle clicks on the job titles word cloud"""
        if event.inaxes != self.titles_ax or not hasattr(self, 'current_titles_wordcloud'):
            return
        try:
            word = self._find_clicked_word(
                int(event.xdata), int(event.ydata),
                self.current_titles_wordcloud.layout_,
            )
            if word:
                self.show_job_title_details(word)
        except Exception as e:
            print(f"Error detecting clicked word: {e}")

    def _build_job_listbox(self, parent: ttk.Frame, jobs: List[Dict], format_fn) -> tk.Listbox:
        """Build a scrollable listbox of jobs with an 'Open Selected URL' button"""
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=('Arial', 9))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        for i, job in enumerate(jobs, 1):
            listbox.insert(tk.END, format_fn(i, job))

        def open_selected():
            selection = listbox.curselection()
            if selection:
                webbrowser.open(jobs[selection[0]]['url'])

        ttk.Button(parent, text="Open Selected URL", command=open_selected).pack(pady=10)
        return listbox

    def add_job(self):
        """Add a job description"""
        job_text = self.job_text.get("1.0", tk.END).strip()
        job_url = self.url_entry.get().strip()

        if not job_text:
            messagebox.showwarning("Warning", "Please enter a job description")
            return
        if not job_url:
            messagebox.showwarning("Warning", "Please enter a job URL")
            return

        result = self.tracker.add_job_description(job_text, job_url)
        extracted_skills = result.get("skills", {})
        job_title = result.get("job_title", "Unspecified Role")

        if not extracted_skills:
            messagebox.showinfo("Info", f"Job Title: {job_title}\n\nNo tech skills found in the job description")
            self.update_titles_wordcloud()
            self.update_stats()
            return

        skill_list = ", ".join(sorted(extracted_skills.keys()))
        messagebox.showinfo("Success",
            f"Job added!\n\nJob Title: {job_title}\n\nFound {len(extracted_skills)} skills:\n{skill_list}")

        self.update_skills_wordcloud()
        self.update_titles_wordcloud()
        self.clear_input()

    def clear_input(self):
        """Clear input fields"""
        self.job_text.delete("1.0", tk.END)
        self.url_entry.delete(0, tk.END)

    def clear_all_data(self):
        """Clear all stored data"""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all data?"):
            self.tracker.clear_all_data()
            self.update_skills_wordcloud()
            self.update_titles_wordcloud()
            messagebox.showinfo("Success", "All data cleared!")

    def show_skill_details(self, skill: str):
        """Show job URLs and job titles for a clicked skill"""
        jobs = self.tracker.get_jobs_for_skill(skill)
        job_titles = self.tracker.get_job_titles_for_skill(skill)
        if not jobs:
            return

        popup = tk.Toplevel(self.root)
        popup.title(f"Details for skill: {skill}")
        popup.geometry("800x600")

        notebook = ttk.Notebook(popup)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        jobs_frame = ttk.Frame(notebook)
        notebook.add(jobs_frame, text=f"Jobs ({len(jobs)})")
        ttk.Label(jobs_frame, text=f"Jobs requiring '{skill}':",
                  font=('Arial', 12, 'bold')).pack(pady=10)
        self._build_job_listbox(
            jobs_frame, jobs,
            lambda i, j: f"{i}. [{j['title']}] {j['url']}",
        )

        titles_frame = ttk.Frame(notebook)
        notebook.add(titles_frame, text=f"Job Titles ({len(job_titles)})")
        ttk.Label(titles_frame, text=f"Job titles requiring '{skill}':",
                  font=('Arial', 12, 'bold')).pack(pady=10)
        titles_list_frame = ttk.Frame(titles_frame)
        titles_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for title, count in sorted(job_titles.items(), key=lambda x: x[1], reverse=True):
            item_frame = ttk.Frame(titles_list_frame)
            item_frame.pack(fill=tk.X, pady=2)
            ttk.Label(item_frame, text=f"{title}: ", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
            ttk.Label(item_frame, text=f"{count} job(s)", font=('Arial', 10)).pack(side=tk.LEFT)

    def show_job_title_details(self, job_title: str):
        """Show jobs and skills for a clicked job title"""
        jobs = self.tracker.get_jobs_for_title(job_title)
        skills = self.tracker.get_skills_for_job_title(job_title)
        if not jobs:
            return

        popup = tk.Toplevel(self.root)
        popup.title(f"Details for: {job_title}")
        popup.geometry("800x600")

        notebook = ttk.Notebook(popup)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        jobs_frame = ttk.Frame(notebook)
        notebook.add(jobs_frame, text=f"Jobs ({len(jobs)})")
        ttk.Label(jobs_frame, text=f"'{job_title}' positions:",
                  font=('Arial', 12, 'bold')).pack(pady=10)

        def format_job(i, job):
            preview = ", ".join(job['skills'][:5])
            if len(job['skills']) > 5:
                preview += "..."
            return f"{i}. {job['url']} | Skills: {preview}"

        self._build_job_listbox(jobs_frame, jobs, format_job)

        skills_frame = ttk.Frame(notebook)
        notebook.add(skills_frame, text=f"Required Skills ({len(skills)})")
        ttk.Label(skills_frame, text=f"Skills required for '{job_title}':",
                  font=('Arial', 12, 'bold')).pack(pady=10)

        canvas = tk.Canvas(skills_frame)
        scrollbar = ttk.Scrollbar(skills_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        for skill, count in sorted(skills.items(), key=lambda x: x[1], reverse=True):
            item_frame = ttk.Frame(scrollable_frame)
            item_frame.pack(fill=tk.X, pady=2, padx=10)
            ttk.Label(item_frame, text=f"{skill}: ", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
            ttk.Label(item_frame, text=f"{count} job(s)", font=('Arial', 10)).pack(side=tk.LEFT)

        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)


def main():
    root = tk.Tk()
    app = JobSkillsGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
