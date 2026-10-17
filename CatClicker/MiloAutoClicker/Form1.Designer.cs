namespace CatClicker
{
    partial class Form1
    {
        private System.ComponentModel.IContainer components = null;

        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        private void InitializeComponent()
        {
            components = new System.ComponentModel.Container();
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(Form1));
            grpClicker = new GroupBox();
            lblHours = new Label();
            numHours = new NumericUpDown();
            lblMins = new Label();
            numMins = new NumericUpDown();
            lblSecs = new Label();
            numSecs = new NumericUpDown();
            lblMS = new Label();
            numMS = new NumericUpDown();
            btnChangeHotKey = new Button();
            btnStart = new Button();
            btnStop = new Button();
            lblClickType = new Label();
            domainClickType = new DomainUpDown();
            chkAdvancedToggle = new CheckBox();
            grpHoldMode = new GroupBox();
            chkRandomize = new CheckBox();
            chkHoldClick = new CheckBox();
            grpStats = new GroupBox();
            lblClickCount = new Label();
            lblCPS = new Label();
            grpRecorder = new GroupBox();
            btnChangeRecordKey = new Button();
            btnChangePlaybackKey = new Button();
            chkLoopPlayback = new CheckBox();
            lstRecordedActions = new ListBox();
            lblRecordStatus = new Label();
            btnPlaybackStart = new Button();
            btnRecordStart = new Button();
            btnSaveMacro = new Button();
            btnLoadMacro = new Button();
            timerClick = new System.Windows.Forms.Timer(components);
            timerRecord = new System.Windows.Forms.Timer(components);
            chkRecordMode = new CheckBox();
            chkDarkMode = new CheckBox();
            grpClicker.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)numHours).BeginInit();
            ((System.ComponentModel.ISupportInitialize)numMins).BeginInit();
            ((System.ComponentModel.ISupportInitialize)numSecs).BeginInit();
            ((System.ComponentModel.ISupportInitialize)numMS).BeginInit();
            grpHoldMode.SuspendLayout();
            grpStats.SuspendLayout();
            grpRecorder.SuspendLayout();
            SuspendLayout();
            // 
            // grpClicker
            // 
            grpClicker.Controls.Add(lblHours);
            grpClicker.Controls.Add(numHours);
            grpClicker.Controls.Add(lblMins);
            grpClicker.Controls.Add(numMins);
            grpClicker.Controls.Add(lblSecs);
            grpClicker.Controls.Add(numSecs);
            grpClicker.Controls.Add(lblMS);
            grpClicker.Controls.Add(numMS);
            grpClicker.Controls.Add(btnChangeHotKey);
            grpClicker.Controls.Add(btnStart);
            grpClicker.Controls.Add(btnStop);
            grpClicker.Controls.Add(lblClickType);
            grpClicker.Controls.Add(domainClickType);
            grpClicker.Controls.Add(chkAdvancedToggle);
            grpClicker.Controls.Add(grpHoldMode);
            grpClicker.Controls.Add(grpStats);
            grpClicker.Location = new Point(12, 40);
            grpClicker.Name = "grpClicker";
            grpClicker.Size = new Size(370, 310);
            grpClicker.TabIndex = 1;
            grpClicker.TabStop = false;
            grpClicker.Text = "Clicker Settings";
            // 
            // lblHours
            // 
            lblHours.Location = new Point(22, 25);
            lblHours.Name = "lblHours";
            lblHours.Size = new Size(70, 23);
            lblHours.TabIndex = 0;
            lblHours.Text = "Hours";
            lblHours.TextAlign = ContentAlignment.MiddleCenter;
            // 
            // numHours
            // 
            numHours.Location = new Point(22, 48);
            numHours.Name = "numHours";
            numHours.Size = new Size(70, 23);
            numHours.TabIndex = 1;
            // 
            // lblMins
            // 
            lblMins.Location = new Point(107, 25);
            lblMins.Name = "lblMins";
            lblMins.Size = new Size(70, 23);
            lblMins.TabIndex = 2;
            lblMins.Text = "Mins";
            lblMins.TextAlign = ContentAlignment.MiddleCenter;
            // 
            // numMins
            // 
            numMins.Location = new Point(107, 48);
            numMins.Name = "numMins";
            numMins.Size = new Size(70, 23);
            numMins.TabIndex = 3;
            // 
            // lblSecs
            // 
            lblSecs.Location = new Point(192, 25);
            lblSecs.Name = "lblSecs";
            lblSecs.Size = new Size(70, 23);
            lblSecs.TabIndex = 4;
            lblSecs.Text = "Secs";
            lblSecs.TextAlign = ContentAlignment.MiddleCenter;
            // 
            // numSecs
            // 
            numSecs.Location = new Point(192, 48);
            numSecs.Name = "numSecs";
            numSecs.Size = new Size(70, 23);
            numSecs.TabIndex = 5;
            // 
            // lblMS
            // 
            lblMS.Location = new Point(277, 25);
            lblMS.Name = "lblMS";
            lblMS.Size = new Size(70, 23);
            lblMS.TabIndex = 6;
            lblMS.Text = "Millisecs";
            lblMS.TextAlign = ContentAlignment.MiddleCenter;
            // 
            // numMS
            // 
            numMS.Location = new Point(277, 48);
            numMS.Maximum = new decimal(new int[] { 999999, 0, 0, 0 });
            numMS.Name = "numMS";
            numMS.Size = new Size(70, 23);
            numMS.TabIndex = 7;
            numMS.Value = new decimal(new int[] { 100, 0, 0, 0 });
            // 
            // btnChangeHotKey
            // 
            btnChangeHotKey.Location = new Point(15, 85);
            btnChangeHotKey.Name = "btnChangeHotKey";
            btnChangeHotKey.Size = new Size(340, 35);
            btnChangeHotKey.TabIndex = 8;
            btnChangeHotKey.Text = "Click to Change HotKey (Current: F6)";
            btnChangeHotKey.Click += btnChangeHotKey_Click;
            // 
            // btnStart
            // 
            btnStart.Location = new Point(15, 130);
            btnStart.Name = "btnStart";
            btnStart.Size = new Size(165, 40);
            btnStart.TabIndex = 9;
            btnStart.Text = "Start (F6)";
            btnStart.Click += btnStart_Click;
            // 
            // btnStop
            // 
            btnStop.Enabled = false;
            btnStop.Location = new Point(190, 130);
            btnStop.Name = "btnStop";
            btnStop.Size = new Size(165, 40);
            btnStop.TabIndex = 10;
            btnStop.Text = "Stop (F6)";
            btnStop.Click += btnStop_Click;
            // 
            // lblClickType
            // 
            lblClickType.Location = new Point(15, 185);
            lblClickType.Name = "lblClickType";
            lblClickType.Size = new Size(65, 23);
            lblClickType.TabIndex = 11;
            lblClickType.Text = "Click Type:";
            // 
            // domainClickType
            // 
            domainClickType.Location = new Point(85, 182);
            domainClickType.Name = "domainClickType";
            domainClickType.ReadOnly = true;
            domainClickType.Size = new Size(95, 23);
            domainClickType.TabIndex = 12;
            // 
            // chkAdvancedToggle
            // 
            chkAdvancedToggle.BackColor = Color.FromArgb(45, 45, 48);
            chkAdvancedToggle.ForeColor = Color.White;
            chkAdvancedToggle.Location = new Point(15, 215);
            chkAdvancedToggle.Name = "chkAdvancedToggle";
            chkAdvancedToggle.Size = new Size(160, 23);
            chkAdvancedToggle.TabIndex = 13;
            chkAdvancedToggle.Text = "Advanced Settings";
            chkAdvancedToggle.UseVisualStyleBackColor = false;
            chkAdvancedToggle.CheckedChanged += chkAdvancedToggle_CheckedChanged;
            // 
            // grpHoldMode
            // 
            grpHoldMode.Controls.Add(chkRandomize);
            grpHoldMode.Controls.Add(chkHoldClick);
            grpHoldMode.Location = new Point(15, 245);
            grpHoldMode.Name = "grpHoldMode";
            grpHoldMode.Size = new Size(340, 50);
            grpHoldMode.TabIndex = 14;
            grpHoldMode.TabStop = false;
            grpHoldMode.Text = "Advanced Settings";
            grpHoldMode.Visible = false;
            // 
            // chkRandomize
            // 
            chkRandomize.BackColor = Color.FromArgb(45, 45, 48);
            chkRandomize.ForeColor = Color.White;
            chkRandomize.Location = new Point(170, 20);
            chkRandomize.Name = "chkRandomize";
            chkRandomize.Size = new Size(160, 23);
            chkRandomize.TabIndex = 13;
            chkRandomize.Text = "Anti-Detection (Jitter)";
            chkRandomize.UseVisualStyleBackColor = false;
            // 
            // chkHoldClick
            // 
            chkHoldClick.BackColor = Color.FromArgb(45, 45, 48);
            chkHoldClick.ForeColor = Color.White;
            chkHoldClick.Location = new Point(10, 20);
            chkHoldClick.Name = "chkHoldClick";
            chkHoldClick.Size = new Size(200, 24);
            chkHoldClick.TabIndex = 0;
            chkHoldClick.Text = "Enable Holding";
            chkHoldClick.UseVisualStyleBackColor = false;
            // 
            // grpStats
            // 
            grpStats.Controls.Add(lblClickCount);
            grpStats.Controls.Add(lblCPS);
            grpStats.Location = new Point(190, 175);
            grpStats.Name = "grpStats";
            grpStats.Size = new Size(165, 65);
            grpStats.TabIndex = 15;
            grpStats.TabStop = false;
            grpStats.Text = "Click Statistics";
            // 
            // lblClickCount
            // 
            lblClickCount.Location = new Point(10, 20);
            lblClickCount.Name = "lblClickCount";
            lblClickCount.Size = new Size(145, 18);
            lblClickCount.TabIndex = 0;
            lblClickCount.Text = "Clicks: 0";
            // 
            // lblCPS
            // 
            lblCPS.Location = new Point(10, 40);
            lblCPS.Name = "lblCPS";
            lblCPS.Size = new Size(145, 18);
            lblCPS.TabIndex = 1;
            lblCPS.Text = "CPS: 0.0";
            // 
            // grpRecorder
            // 
            grpRecorder.Controls.Add(btnChangeRecordKey);
            grpRecorder.Controls.Add(btnChangePlaybackKey);
            grpRecorder.Controls.Add(chkLoopPlayback);
            grpRecorder.Controls.Add(lstRecordedActions);
            grpRecorder.Controls.Add(lblRecordStatus);
            grpRecorder.Controls.Add(btnPlaybackStart);
            grpRecorder.Controls.Add(btnRecordStart);
            grpRecorder.Controls.Add(btnSaveMacro);
            grpRecorder.Controls.Add(btnLoadMacro);
            grpRecorder.Location = new Point(400, 40);
            grpRecorder.Name = "grpRecorder";
            grpRecorder.Size = new Size(200, 310);
            grpRecorder.TabIndex = 2;
            grpRecorder.TabStop = false;
            grpRecorder.Text = "Recording Settings";
            // 
            // btnChangeRecordKey
            // 
            btnChangeRecordKey.Enabled = false;
            btnChangeRecordKey.Location = new Point(10, 22);
            btnChangeRecordKey.Name = "btnChangeRecordKey";
            btnChangeRecordKey.Size = new Size(88, 30);
            btnChangeRecordKey.TabIndex = 0;
            btnChangeRecordKey.Text = "Key: F7";
            btnChangeRecordKey.Click += btnChangeRecordKey_Click;
            // 
            // btnChangePlaybackKey
            // 
            btnChangePlaybackKey.Enabled = false;
            btnChangePlaybackKey.Location = new Point(102, 22);
            btnChangePlaybackKey.Name = "btnChangePlaybackKey";
            btnChangePlaybackKey.Size = new Size(88, 30);
            btnChangePlaybackKey.TabIndex = 1;
            btnChangePlaybackKey.Text = "Key: F8";
            btnChangePlaybackKey.Click += btnChangePlaybackKey_Click;
            // 
            // chkLoopPlayback
            // 
            chkLoopPlayback.BackColor = Color.FromArgb(45, 45, 48);
            chkLoopPlayback.Enabled = false;
            chkLoopPlayback.ForeColor = Color.White;
            chkLoopPlayback.Location = new Point(10, 90);
            chkLoopPlayback.Name = "chkLoopPlayback";
            chkLoopPlayback.Size = new Size(104, 24);
            chkLoopPlayback.TabIndex = 2;
            chkLoopPlayback.Text = "Loop Playback";
            chkLoopPlayback.UseVisualStyleBackColor = false;
            // 
            // lstRecordedActions
            // 
            lstRecordedActions.Enabled = false;
            lstRecordedActions.ItemHeight = 15;
            lstRecordedActions.Location = new Point(10, 115);
            lstRecordedActions.Name = "lstRecordedActions";
            lstRecordedActions.Size = new Size(180, 94);
            lstRecordedActions.TabIndex = 3;
            // 
            // lblRecordStatus
            // 
            lblRecordStatus.Enabled = false;
            lblRecordStatus.Location = new Point(10, 275);
            lblRecordStatus.Name = "lblRecordStatus";
            lblRecordStatus.Size = new Size(180, 23);
            lblRecordStatus.TabIndex = 4;
            lblRecordStatus.Text = "Status: Idle";
            // 
            // btnPlaybackStart
            // 
            btnPlaybackStart.Enabled = false;
            btnPlaybackStart.Location = new Point(102, 55);
            btnPlaybackStart.Name = "btnPlaybackStart";
            btnPlaybackStart.Size = new Size(88, 30);
            btnPlaybackStart.TabIndex = 5;
            btnPlaybackStart.Text = "Playback";
            btnPlaybackStart.Click += btnPlaybackStart_Click;
            // 
            // btnRecordStart
            // 
            btnRecordStart.Enabled = false;
            btnRecordStart.Location = new Point(10, 55);
            btnRecordStart.Name = "btnRecordStart";
            btnRecordStart.Size = new Size(88, 30);
            btnRecordStart.TabIndex = 6;
            btnRecordStart.Text = "Record";
            btnRecordStart.Click += btnRecordStart_Click;
            // 
            // btnSaveMacro
            // 
            btnSaveMacro.Enabled = false;
            btnSaveMacro.Location = new Point(10, 220);
            btnSaveMacro.Name = "btnSaveMacro";
            btnSaveMacro.Size = new Size(88, 30);
            btnSaveMacro.TabIndex = 7;
            btnSaveMacro.Text = "Save";
            btnSaveMacro.Click += btnSaveMacro_Click;
            // 
            // btnLoadMacro
            // 
            btnLoadMacro.Enabled = false;
            btnLoadMacro.Location = new Point(102, 220);
            btnLoadMacro.Name = "btnLoadMacro";
            btnLoadMacro.Size = new Size(88, 30);
            btnLoadMacro.TabIndex = 8;
            btnLoadMacro.Text = "Load";
            btnLoadMacro.Click += btnLoadMacro_Click;
            // 
            // timerClick
            // 
            timerClick.Interval = 10;
            timerClick.Tick += timerClick_Tick;
            // 
            // timerRecord
            // 
            timerRecord.Interval = 10;
            timerRecord.Tick += timerRecord_Tick;
            // 
            // chkRecordMode
            // 
            chkRecordMode.AutoSize = true;
            chkRecordMode.Location = new Point(400, 18);
            chkRecordMode.Name = "chkRecordMode";
            chkRecordMode.Size = new Size(123, 19);
            chkRecordMode.TabIndex = 3;
            chkRecordMode.Text = "Enable Recording?";
            chkRecordMode.CheckedChanged += chkRecordMode_CheckedChanged;
            // 
            // chkDarkMode
            // 
            chkDarkMode.AutoSize = true;
            chkDarkMode.Location = new Point(12, 12);
            chkDarkMode.Name = "chkDarkMode";
            chkDarkMode.Size = new Size(89, 19);
            chkDarkMode.TabIndex = 0;
            chkDarkMode.Text = "Dark Mode?";
            chkDarkMode.CheckedChanged += chkDarkMode_CheckedChanged;
            // 
            // Form1
            // 
            ClientSize = new Size(612, 365);
            Controls.Add(chkDarkMode);
            Controls.Add(grpClicker);
            Controls.Add(grpRecorder);
            Controls.Add(chkRecordMode);
            FormBorderStyle = FormBorderStyle.FixedSingle;
            Icon = (Icon)resources.GetObject("$this.Icon");
            MaximizeBox = false;
            Name = "Form1";
            Text = "CatClicker by Milo";
            grpClicker.ResumeLayout(false);
            ((System.ComponentModel.ISupportInitialize)numHours).EndInit();
            ((System.ComponentModel.ISupportInitialize)numMins).EndInit();
            ((System.ComponentModel.ISupportInitialize)numSecs).EndInit();
            ((System.ComponentModel.ISupportInitialize)numMS).EndInit();
            this.timerRecord.Tick += new System.EventHandler(this.timerRecord_Tick);
            this.timerRecord.Interval = 10;
            grpHoldMode.ResumeLayout(false);
            grpStats.ResumeLayout(false);
            grpRecorder.ResumeLayout(false);
            ResumeLayout(false);
            PerformLayout();
        }

        #endregion

        private System.Windows.Forms.GroupBox grpClicker, grpRecorder;
        private System.Windows.Forms.Button btnChangeHotKey, btnStart, btnStop, btnRecordStart, btnPlaybackStart;
        private System.Windows.Forms.Button btnChangeRecordKey, btnChangePlaybackKey, btnSaveMacro, btnLoadMacro;
        private System.Windows.Forms.DomainUpDown domainClickType;
        private System.Windows.Forms.CheckBox chkRandomize, chkRecordMode, chkLoopPlayback, chkDarkMode;
        private System.Windows.Forms.Timer timerClick, timerRecord;
        private System.Windows.Forms.NumericUpDown numHours, numMins, numSecs, numMS;
        private System.Windows.Forms.Label lblHours, lblMins, lblSecs, lblMS, lblRecordStatus, lblClickType;
        private System.Windows.Forms.ListBox lstRecordedActions;
        private System.Windows.Forms.GroupBox grpHoldMode;
        private System.Windows.Forms.CheckBox chkHoldClick;
        private System.Windows.Forms.CheckBox chkAdvancedToggle;
        private System.Windows.Forms.GroupBox grpStats;
        private System.Windows.Forms.Label lblClickCount;
        private System.Windows.Forms.Label lblCPS;
    }
}