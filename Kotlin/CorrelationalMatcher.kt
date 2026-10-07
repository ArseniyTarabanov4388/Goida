package com.example.myapplication

import android.content.Context
import android.util.Log
import java.io.BufferedReader
import java.io.InputStreamReader
import kotlin.math.abs
import kotlin.math.sqrt

data class ReferencePoint(
    val pointNum: Int,
    val y: Double,
    val btMean: Double
)

data class DoorPoint(
    val name: String,
    val y: Double
)

data class MatchResult(
    val bestY: Double,
    val maxCorrelation: Double,
    val nearestDoor: String
)

class CorrelationalMatcher(private val context: Context) {

    private val referenceMap = mutableListOf<ReferencePoint>()
    private val doors = mutableListOf<DoorPoint>()

    init {
        loadReferenceSummary("processed_magnetic_summary.csv")
        loadDoors("doors.csv")
    }

    private fun loadReferenceSummary(fileName: String) {
        try {
            val inputStream = context.assets.open(fileName)
            val reader = BufferedReader(InputStreamReader(inputStream))

            val headerLine = reader.readLine() ?: return
            val delimiter = if (headerLine.contains(";")) ";" else ","
            val headers = headerLine.split(delimiter).map { it.trim().removeSurrounding("\"").lowercase() }

            val numIdx = headers.indexOfFirst { it.contains("point_num") || it.contains("num") }
            val yIdx = headers.indexOfFirst { it == "y" }
            val btIdx = headers.indexOfFirst { it.contains("bt_mean") || it.contains("bt") }

            Log.d("TEST_MATCHER", "Заголовки $fileName -> Y: $yIdx, BT_mean: $btIdx")

            reader.forEachLine { line ->
                val tokens = line.split(delimiter).map { it.trim().removeSurrounding("\"") }
                if (tokens.size > maxOf(yIdx, btIdx) && yIdx != -1 && btIdx != -1) {
                    val pNum = if (numIdx != -1 && tokens.size > numIdx) tokens[numIdx].toIntOrNull() ?: 0 else 0
                    val y = tokens[yIdx].toDoubleOrNull() ?: 0.0
                    val bt = tokens[btIdx].toDoubleOrNull() ?: 0.0

                    referenceMap.add(ReferencePoint(pNum, y, bt))
                }
            }
            reader.close()
            Log.d("TEST_MATCHER", "Загружено точек эталонной карты: ${referenceMap.size}")
        } catch (e: Exception) {
            Log.e("TEST_MATCHER", "Ошибка загрузки $fileName: ${e.message}")
        }
    }

    private fun loadDoors(fileName: String) {
        try {
            val inputStream = context.assets.open(fileName)
            val reader = BufferedReader(InputStreamReader(inputStream))

            val headerLine = reader.readLine() ?: return
            val delimiter = if (headerLine.contains(";")) ";" else ","
            val headers = headerLine.split(delimiter).map { it.trim().removeSurrounding("\"").lowercase() }

            val nameIdx = headers.indexOfFirst { it.contains("door") || it.contains("name") }
            val yIdx = headers.indexOfFirst { it == "y" }

            reader.forEachLine { line ->
                val tokens = line.split(delimiter).map { it.trim().removeSurrounding("\"") }
                if (tokens.size > maxOf(nameIdx, yIdx) && nameIdx != -1 && yIdx != -1) {
                    val name = tokens[nameIdx]
                    val y = tokens[yIdx].toDoubleOrNull() ?: 0.0

                    doors.add(DoorPoint(name, y))
                }
            }
            reader.close()
            Log.d("TEST_MATCHER", "Загружено дверей: ${doors.size}")
        } catch (e: Exception) {
            Log.e("TEST_MATCHER", "Ошибка загрузки $fileName: ${e.message}")
        }
    }

    private fun calculatePearsonCorrelation(x: DoubleArray, y: DoubleArray): Double {
        if (x.size != y.size || x.isEmpty()) return 0.0

        val n = x.size
        val meanX = x.average()
        val meanY = y.average()

        var num = 0.0
        var denX = 0.0
        var denY = 0.0

        for (i in 0 until n) {
            val diffX = x[i] - meanX
            val diffY = y[i] - meanY
            num += diffX * diffY
            denX += diffX * diffX
            denY += diffY * diffY
        }

        val den = sqrt(denX * denY)
        return if (den == 0.0) 0.0 else num / den
    }

    fun findBestMatch(sampleTrajectory: DoubleArray, targetZ: Double? = null): MatchResult? {
        if (sampleTrajectory.isEmpty() || referenceMap.isEmpty()) {
            Log.e("TEST_MATCHER", "Ошибка: тестовая выборка или эталонная карта пуста")
            return null
        }

        val windowSize = sampleTrajectory.size
        if (referenceMap.size < windowSize) {
            Log.e("TEST_MATCHER", "Размер выборки ($windowSize) больше количества точек в карты (${referenceMap.size})")
            return null
        }

        var maxCorr = -1.0
        var bestPoint = referenceMap.first()

        for (i in 0..(referenceMap.size - windowSize)) {
            val refWindow = DoubleArray(windowSize) { idx -> referenceMap[i + idx].btMean }
            val corr = calculatePearsonCorrelation(sampleTrajectory, refWindow)

            if (corr > maxCorr) {
                maxCorr = corr
                bestPoint = referenceMap[i + windowSize / 2]
            }
        }

        val nearestDoor = findNearestDoor(bestPoint.y)

        return MatchResult(
            bestY = bestPoint.y,
            maxCorrelation = maxCorr,
            nearestDoor = nearestDoor
        )
    }

    private fun findNearestDoor(y: Double): String {
        if (doors.isEmpty()) return "Двери не найдены"

        var minDistance = Double.MAX_VALUE
        var nearestName = "Неизвестно"

        for (door in doors) {
            val dist = abs(door.y - y)
            if (dist < minDistance) {
                minDistance = dist
                nearestName = door.name
            }
        }

        return "$nearestName (расстояние: ${String.format("%.1f", minDistance)} м)"
    }
}