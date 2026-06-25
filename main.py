import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from win10toast import ToastNotifier

DB_NAME = "task_planner.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            deadline DATETIME,
            priority TEXT CHECK(priority IN ('Высокий', 'Средний', 'Низкий')),
            status TEXT DEFAULT 'Не выполнена' CHECK(status IN ('Выполнена', 'Не выполнена')),
            category_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            old_status TEXT,
            new_status TEXT NOT NULL,
            change_type TEXT DEFAULT 'status_change',
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category_id)")
    
    cur.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Работа'), ('Личное'), ('Учёба'), ('Здоровье'), ('Финансы')")
    conn.commit()
    conn.close()

def check_deadlines():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT title, deadline, id 
        FROM tasks 
        WHERE status = 'Не выполнена' 
        AND deadline IS NOT NULL 
        AND DATE(deadline) <= DATE('now')
    """)
    tasks = cur.fetchall()
    conn.close()
    
    if tasks:
        toaster = ToastNotifier()
        for title, deadline, task_id in tasks:
            message = f"Задача '{title}' просрочена или должна быть выполнена сегодня (до {deadline})!"
            toaster.show_toast(
                "⚠️ Напоминание о дедлайне",
                message,
                duration=10,
                threaded=True
            )

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Планировщик личных задач")
        self.root.geometry("900x500")
        self.create_widgets()
        self.load_tasks()

    def create_widgets(self):
        filter_frame = ttk.LabelFrame(self.root, text="Фильтры", padding=10)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(filter_frame, text="Категория:").grid(row=0, column=0, padx=5)
        self.filter_category = ttk.Combobox(filter_frame, values=["Все"] + self.get_categories(), state="readonly", width=15)
        self.filter_category.set("Все")
        self.filter_category.grid(row=0, column=1, padx=5)

        ttk.Label(filter_frame, text="Приоритет:").grid(row=0, column=2, padx=5)
        self.filter_priority = ttk.Combobox(filter_frame, values=["Все", "Высокий", "Средний", "Низкий"], state="readonly", width=10)
        self.filter_priority.set("Все")
        self.filter_priority.grid(row=0, column=3, padx=5)

        ttk.Label(filter_frame, text="Статус:").grid(row=0, column=4, padx=5)
        self.filter_status = ttk.Combobox(filter_frame, values=["Все", "Выполнена", "Не выполнена"], state="readonly", width=12)
        self.filter_status.set("Все")
        self.filter_status.grid(row=0, column=5, padx=5)

        ttk.Button(filter_frame, text="🔍 Применить фильтр", command=self.load_tasks).grid(row=0, column=6, padx=20)

        columns = ("ID", "Название", "Категория", "Приоритет", "Статус", "Дедлайн")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
            if col == "ID":
                self.tree.column(col, width=40)
            elif col == "Название":
                self.tree.column(col, width=250)
            else:
                self.tree.column(col, width=100)
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="➕ Добавить", command=self.add_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✏️ Редактировать", command=self.edit_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ Удалить", command=self.delete_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✅ Отметить выполнено", command=self.mark_done).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📊 Отчёт", command=self.show_report).pack(side=tk.LEFT, padx=5)

    def get_categories(self):
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT name FROM categories ORDER BY name")
        categories = [row[0] for row in cur.fetchall()]
        conn.close()
        return categories

    def load_tasks(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        query = """
            SELECT t.id, t.title, c.name, t.priority, t.status, t.deadline
            FROM tasks t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE 1=1
        """
        params = []

        category = self.filter_category.get()
        if category != "Все":
            query += " AND c.name = ?"
            params.append(category)

        priority = self.filter_priority.get()
        if priority != "Все":
            query += " AND t.priority = ?"
            params.append(priority)

        status = self.filter_status.get()
        if status != "Все":
            query += " AND t.status = ?"
            params.append(status)

        query += " ORDER BY t.deadline ASC NULLS LAST"
        
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(query, params)
        
        for row in cur.fetchall():
            self.tree.insert("", tk.END, values=row)
        
        conn.close()

    def add_task(self):
        self.open_task_window()

    def edit_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите задачу для редактирования")
            return
        task_id = self.tree.item(selected[0])["values"][0]
        self.open_task_window(task_id)

    def delete_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите задачу для удаления")
            return
        
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить задачу?"):
            task_id = self.tree.item(selected[0])["values"][0]
            conn = sqlite3.connect(DB_NAME)
            conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            conn.commit()
            conn.close()
            self.load_tasks()
            messagebox.showinfo("Успех", "Задача удалена")

    def mark_done(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите задачу")
            return
        
        task_id = self.tree.item(selected[0])["values"][0]
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("SELECT status FROM tasks WHERE id=?", (task_id,))
        old_status = cur.fetchone()[0]
        
        if old_status == "Выполнена":
            messagebox.showinfo("Информация", "Задача уже выполнена")
            conn.close()
            return

        cur.execute("UPDATE tasks SET status='Выполнена', updated_at=CURRENT_TIMESTAMP WHERE id=?", (task_id,))

        cur.execute("""
            INSERT INTO task_history (task_id, old_status, new_status, change_type) 
            VALUES (?, ?, ?, 'status_change')
        """, (task_id, old_status, "Выполнена"))
        
        conn.commit()
        conn.close()
        self.load_tasks()
        messagebox.showinfo("Успех", "Задача отмечена как выполненная")

    def open_task_window(self, task_id=None):
        win = tk.Toplevel(self.root)
        win.title("Добавление/Редактирование задачи")
        win.geometry("500x450")
        win.grab_set()

        ttk.Label(win, text="Название:", font=("Arial", 10, "bold")).pack(pady=(10,0))
        title_entry = ttk.Entry(win, width=50)
        title_entry.pack(pady=5)
        
        ttk.Label(win, text="Описание:", font=("Arial", 10, "bold")).pack(pady=(10,0))
        desc_text = tk.Text(win, height=4, width=50)
        desc_text.pack(pady=5)
        
        ttk.Label(win, text="Категория:", font=("Arial", 10, "bold")).pack(pady=(10,0))
        cat_combo = ttk.Combobox(win, values=self.get_categories(), state="readonly", width=30)
        cat_combo.pack(pady=5)
        
        ttk.Label(win, text="Приоритет:", font=("Arial", 10, "bold")).pack(pady=(10,0))
        priority_combo = ttk.Combobox(win, values=["Высокий", "Средний", "Низкий"], state="readonly", width=30)
        priority_combo.pack(pady=5)
        
        ttk.Label(win, text="Дедлайн (ГГГГ-ММ-ДД):", font=("Arial", 10, "bold")).pack(pady=(10,0))
        deadline_entry = ttk.Entry(win, width=30)
        deadline_entry.pack(pady=5)

        if task_id:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("""
                SELECT title, description, deadline, priority, category_id 
                FROM tasks WHERE id=?
            """, (task_id,))
            row = cur.fetchone()
            if row:
                title_entry.insert(0, row[0])
                desc_text.insert("1.0", row[1] or "")
                if row[2]:
                    deadline_entry.insert(0, row[2])
                priority_combo.set(row[3])

                if row[4]:
                    cur.execute("SELECT name FROM categories WHERE id=?", (row[4],))
                    cat_name = cur.fetchone()
                    if cat_name:
                        cat_combo.set(cat_name[0])
            conn.close()

        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=20)
        
        def save():
            if not title_entry.get().strip():
                messagebox.showerror("Ошибка", "Название задачи обязательно")
                return

            category_name = cat_combo.get()
            category_id = None
            if category_name:
                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()
                cur.execute("SELECT id FROM categories WHERE name=?", (category_name,))
                res = cur.fetchone()
                if res:
                    category_id = res[0]
                conn.close()

            conn = sqlite3.connect(DB_NAME)
            if task_id:
                conn.execute("""
                    UPDATE tasks 
                    SET title=?, description=?, deadline=?, priority=?, category_id=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                """, (title_entry.get(), desc_text.get("1.0", tk.END).strip(), 
                      deadline_entry.get() or None, priority_combo.get(), category_id, task_id))
            else:
                conn.execute("""
                    INSERT INTO tasks (title, description, deadline, priority, category_id, status) 
                    VALUES (?, ?, ?, ?, ?, 'Не выполнена')
                """, (title_entry.get(), desc_text.get("1.0", tk.END).strip(), 
                      deadline_entry.get() or None, priority_combo.get(), category_id))
            
            conn.commit()
            conn.close()
            win.destroy()
            self.load_tasks()
            messagebox.showinfo("Успех", "Задача сохранена")
        
        ttk.Button(btn_frame, text="💾 Сохранить", command=save).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="❌ Отмена", command=win.destroy).pack(side=tk.LEFT, padx=10)

    def show_report(self):
        report_win = tk.Toplevel(self.root)
        report_win.title("Отчёт по задачам")
        report_win.geometry("500x400")
        report_win.grab_set()

        ttk.Label(report_win, text="📊 Статистика выполнения задач", 
                  font=("Arial", 14, "bold")).pack(pady=10)
        
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM tasks WHERE status='Выполнена'")
        completed = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM tasks WHERE status='Не выполнена'")
        not_completed = cur.fetchone()[0]
        
        total = completed + not_completed
        percent = (completed / total * 100) if total > 0 else 0

        info_frame = ttk.LabelFrame(report_win, text="Общая статистика", padding=10)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(info_frame, text=f"✅ Выполнено: {completed} задач", 
                  font=("Arial", 11)).pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"❌ Не выполнено: {not_completed} задач", 
                  font=("Arial", 11)).pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"📈 Процент выполнения: {percent:.1f}%", 
                  font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=5)

        bar_length = 30
        filled = int(bar_length * percent / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        ttk.Label(info_frame, text=bar, font=("Courier", 10)).pack(pady=5)

        cat_frame = ttk.LabelFrame(report_win, text="По категориям", padding=10)
        cat_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        cur.execute("""
            SELECT c.name,
                   SUM(CASE WHEN t.status = 'Выполнена' THEN 1 ELSE 0 END) as completed,
                   SUM(CASE WHEN t.status = 'Не выполнена' THEN 1 ELSE 0 END) as not_completed
            FROM categories c
            LEFT JOIN tasks t ON c.id = t.category_id
            GROUP BY c.name
            ORDER BY c.name
        """)
        
        for cat_name, cat_completed, cat_not in cur.fetchall():
            cat_total = (cat_completed or 0) + (cat_not or 0)
            if cat_total > 0:
                ttk.Label(cat_frame, text=f"• {cat_name}: {cat_completed or 0} выполнено / {cat_not or 0} не выполнено",
                         font=("Arial", 10)).pack(anchor=tk.W, pady=2)
        
        conn.close()
        
        ttk.Button(report_win, text="Закрыть", command=report_win.destroy).pack(pady=20)

if __name__ == "__main__":
    init_db()
    check_deadlines()
    root = tk.Tk()
    app = App(root)
    root.mainloop()
