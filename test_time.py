from datetime import datetime, timezone
current_time = datetime.now(timezone.utc)
print(current_time)  # 2025-04-05 12:34:56.789012+00:00

from torch import nn

class MyModel(nn.Module):
    def __init__(self, input_size, hidden_size, output_size, dropout_rate):
        super(MyModel, self).__init__()
        self.fc1 = nn.Linear(10, 10)
        self.dropout = nn.Dropout(dropout_rate)
        self.relu = nn.ReLU()
        self.batch_norm = nn.BatchNorm1d(hidden_size)
        self.fc2 = nn.Linear(10, 10)

    def forward(self, x):
        x = self.fc1(x)
        x = self.dropout(x)
        x = self.relu(x)
        x = self.batch_norm(x)
        x = self.fc2(x)
        return x

model = MyModel()