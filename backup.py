import pandas as pd
from datetime import datetime
from app import db, Client

def perform_backup():
    clients = Client.query.all()
    data = [{
        'Name': c.name,
        'Contact': c.contact,
        'Goal': c.goal,
        'Weight': c.weight,
        'Payment Status': c.payment_status,
        'Join Date': c.join_date,
        'Due Date': c.payment_due_date,
        'Last Updated': c.last_updated,
    } for c in clients]

    df = pd.DataFrame(data)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f'static/backups/backup_{timestamp}.xlsx'
    df.to_excel(filename, index=False)




# from app import db, Client
# import pandas as pd
# from datetime import datetime
# import os

# def backup_data():
#     data = Client.query.all()
#     rows = [{
#         "Name": c.name,
#         "Contact": c.contact,
#         "Goal": c.goal,
#         "Weight": c.weight,
#         "Status": c.payment_status,
#         "Join Date": c.join_date,
#         "Due Date": c.payment_due_date,
#         "Updated": c.last_updated,
#     } for c in data]

#     df = pd.DataFrame(rows)

#     backup_dir = "backups"
#     os.makedirs(backup_dir, exist_ok=True)

#     filename = f"backup_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"
#     filepath = os.path.join(backup_dir, filename)

#     df.to_excel(filepath, index=False, engine='openpyxl')
#     print(f"✅ Backup saved to {filepath}")

# if __name__ == '__main__':
#     with app.app_context():
#         backup_data()
