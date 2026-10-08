package com.example.myapplication

import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.sqrt

class MainActivity : ComponentActivity(), SensorEventListener {

    private lateinit var sensorManager: SensorManager
    private var magnetometer: Sensor? = null
    private lateinit var matcher: CorrelationalMatcher

    private val windowSize = 7
    private val trajectoryBuffer = ArrayDeque<Double>(windowSize)

    private var lastSampleTime = 0L
    private val sampleIntervalMs = 500L // Фиксируем замер не чаще, чем раз в 500 мс (~0.5 м ходьбы)

    private var currentYText by mutableStateOf("Пройдите первые ~3.5 м...")
    private var nearestDoorText by mutableStateOf("—")
    private var correlationText by mutableStateOf("—")
    private var rawBtText by mutableStateOf("0.0 µT")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        matcher = CorrelationalMatcher(this)

        sensorManager = getSystemService(SENSOR_SERVICE) as SensorManager
        magnetometer = sensorManager.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD)

        setContent {
            Surface(
                modifier = Modifier.fillMaxSize(),
                color = MaterialTheme.colorScheme.background
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Магнитный Навигатор",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(bottom = 24.dp)
                    )

                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text(
                                text = "Текущая позиция (Y):",
                                fontSize = 14.sp,
                                color = MaterialTheme.colorScheme.outline
                            )
                            Text(
                                text = currentYText,
                                fontSize = 24.sp,
                                fontWeight = FontWeight.Bold
                            )

                            Spacer(modifier = Modifier.height(16.dp))

                            Text(
                                text = "Ближайшее помещение:",
                                fontSize = 14.sp,
                                color = MaterialTheme.colorScheme.outline
                            )
                            Text(
                                text = nearestDoorText,
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Medium
                            )

                            Spacer(modifier = Modifier.height(16.dp))

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(text = "Корреляция: $correlationText", fontSize = 12.sp)
                                Text(text = "Индукция: $rawBtText", fontSize = 12.sp)
                            }
                        }
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        magnetometer?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }
    }

    override fun onPause() {
        super.onPause()
        sensorManager.unregisterListener(this)
    }

    override fun onSensorChanged(event: SensorEvent?) {
        if (event?.sensor?.type == Sensor.TYPE_MAGNETIC_FIELD) {
            val currentTime = System.currentTimeMillis()

            if (currentTime - lastSampleTime >= sampleIntervalMs) {
                lastSampleTime = currentTime

                val bx = event.values[0]
                val by = event.values[1]
                val bz = event.values[2]

                val bt = sqrt((bx * bx + by * by + bz * bz).toDouble())
                rawBtText = String.format("%.1f µT", bt)

                if (trajectoryBuffer.size >= windowSize) {
                    trajectoryBuffer.removeFirst()
                }
                trajectoryBuffer.addLast(bt)

                if (trajectoryBuffer.size == windowSize) {
                    val currentTrajectory = trajectoryBuffer.toDoubleArray()
                    val result = matcher.findBestMatch(currentTrajectory)

                    if (result != null) {
                        currentYText = "${String.format("%.1f", result.bestY)} м"
                        nearestDoorText = result.nearestDoor
                        correlationText = String.format("%.3f", result.maxCorrelation)
                    }
                }
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
}