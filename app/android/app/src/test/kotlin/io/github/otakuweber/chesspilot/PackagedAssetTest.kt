package io.github.otakuweber.chesspilot

import java.io.File
import java.io.IOException
import java.io.InputStream
import java.nio.file.Files
import java.nio.file.StandardCopyOption.ATOMIC_MOVE
import java.nio.file.StandardCopyOption.REPLACE_EXISTING
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class PackagedAssetTest {
    @get:Rule val folder = TemporaryFolder()
    private val abc = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    private val hello = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    private val replace: (File, File) -> Unit = { source, destination ->
        Files.move(source.toPath(), destination.toPath(), ATOMIC_MOVE, REPLACE_EXISTING)
    }

    @Test fun installsReusesUpgradesAndRepairsThePackagedModel() {
        val target = File(folder.root, "chess_detection.onnx")
        installPackagedAsset(target, abc) { "abc".byteInputStream() }
        assertEquals("abc", target.readText())
        installPackagedAsset(target, abc) { error("A matching model must be reused") }
        installPackagedAsset(target, hello, replace) { "hello".byteInputStream() }
        assertEquals("hello", target.readText())
        target.writeText("corrupt cached model")
        File(folder.root, "chess_detection.onnx.part").writeText("interrupted previous copy")
        installPackagedAsset(target, hello, replace) { "hello".byteInputStream() }
        assertEquals("hello", target.readText())
        assertFalse(File(folder.root, "chess_detection.onnx.part").exists())
    }

    @Test fun invalidOrInterruptedCopiesPreserveThePreviousModelAndRemovePartialFiles() {
        val target = folder.newFile("chess_detection.onnx").apply { writeText("abc") }
        assertThrows(IllegalStateException::class.java) {
            installPackagedAsset(target, hello) { "wrong package data".byteInputStream() }
        }
        assertEquals("abc", target.readText())
        assertFalse(File(folder.root, "chess_detection.onnx.part").exists())
        assertThrows(IOException::class.java) {
            installPackagedAsset(target, hello) {
                object : InputStream() {
                    override fun read(): Int = throw IOException("Interrupted copy")
                }
            }
        }
        assertEquals("abc", target.readText())
        assertFalse(File(folder.root, "chess_detection.onnx.part").exists())
    }

    @Test fun badChecksumsAndUnreplaceableTargetsFailBeforeUsingTheWrongModel() {
        val target = folder.newFolder("chess_detection.onnx")
        val retained = File(target, "existing").apply { writeText("keep") }
        assertThrows(IllegalStateException::class.java) {
            installPackagedAsset(target, "invalid checksum") { error("Must not open asset") }
        }
        assertThrows(IllegalStateException::class.java) {
            installPackagedAsset(target, hello) { "hello".byteInputStream() }
        }
        assertEquals("keep", retained.readText())
        assertFalse(File(folder.root, "chess_detection.onnx.part").exists())
    }
}
